# B67: recoverable party-save copy, preserving the last good game

Date: 2026-11-10. Source: this user's pinned `ProhorovIlja/bloodborne_pc_windows_port` master and its upstream `visy/bloodborne_pc_windows_port`. Related Ultimate [save quarantine PR #132](https://github.com/ProhorovIlja/BBSC-Yharnam-Together/pull/132), which remains offline and never promotes to active saves.

## Why the old code was dangerous

The original local `scripts/party_saves.py::copy_solo_to_party(replace=True)` deleted `savedata_party` with `shutil.rmtree(party)` before promoting a new staging directory. On failure, a player could lose the active party save folder. The newer visy version improves immediate rollback by renaming the old party to `savedata_party.replaced` first, but it deletes any older `.replaced` copy at the start and removes the displaced copy after promotion. Both are unacceptable for our longer-term no-loss requirement.

## Implemented in this Windows-port repo (not a speculative Ultimate merge)

`scripts/party_saves.py` now:
- refuses source/target symlinks and non-regular inputs, ignores unfinished `*.bbtmp`, and checks SHA-256 + size for every copied regular file; detects source changes through a second scan;
- serializes copy requests using an exclusive `.party-copy.lock`. A leftover crash lock is **NOT silently removed**: stop all game/launcher processes and inspect before manual recovery;
- uses an unguessable temporary `.savedata_party.copying-<token>` folder, never deletes or reuses another session's staging path;
- on explicit `replace=True`, atomically *moves the existing party directory* to a uniquely named backup `user/save_backups/savedata_party/<timestamp>-<token>.pending-replaced`, then renames the verified staging directory into its original place. It does **NOT** delete the original or an earlier backup;
- after promotion, renames the old folder to `...-replaced` and returns that backup path. If the second rename fails, tries to restore the old directory. If restoration fails, old data stays intact in the `.pending-replaced` directory instead of being destroyed;
- recognizes an interrupted pending backup during the next invocation: if party is absent and **exactly one** pending backup exists, it restores that backup and deliberately aborts the new replacement, requiring manual inspection before retry. If party is already present after successful promotion, prior pending backups are finalized without replacing the current save;
- retains the previous `copy_solo_to_party(user, replace=False)` first-time behavior, including an existing empty party folder and returning `None` when it replaced no actual save.

`tests/test_party_saves.py` adds temporary-fixture regression for repeated replacements preserving older backups, controlled rename failure and rollback, process-interrupt window, rollback failure with protected pending data, byte corruption of equal-sized files, overlapping copy lock, stale backup finalization, empty party folder and symlink rejection. All tests operate under `tempfile.TemporaryDirectory`, not player data.

## Limitations and release gates

This two-rename protocol is **recoverable** with a preserved old directory but is not an indivisible cross-directory transaction. Power loss between moves can temporarily leave `savedata_party` missing while its old contents remain in the unique `.pending-replaced` backup; automatic restoration only happens on a subsequent explicit copy attempt. The launcher currently does **not** run startup recovery before launching the game. Until that is implemented and real Windows gameplay verified, keep the PR **Draft**; do not claim a ready-to-release save safety fix.

The routine is for offline/save-closed operations only. Cross-device path and antivirus failures, system crash/fsync durability, concurrent game writes, all 1.09 title IDs and network/lobby slot identity still require dedicated validation. The lock is fail-closed, not an automatic stale-lock breaker. Do not run it against active game saves or Fornex production from this chat. A true one-click install in Ultimate must also satisfy its `HomeWorlds` and phantom-item ledgers and must not share YT and direct P2P save namespaces by accident.

License: this repo is GPL-3.0-or-later. Separate Ultimate GPLv2-only third-party catalog remains a redistribution compatibility blocker. No game binaries or copyrighted assets added.
