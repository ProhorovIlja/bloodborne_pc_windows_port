# V234: launcher mod preflight source containment and honest risk counts

2026-11-01. Draft PR #85; additive source-only hardening of V232, based on
the pinned public Yharnam Together v1.3.1 mod loader
(`lKaniel/bloodborne-server` commit `5d2305ee611ef1e03be39ff925f0da75c9a70393`).

## Why

V232 already detects case-insensitive whole-file collisions and follows
the real upstream mod order. Two edge cases remained:

1. A mod file could appear to be an ordinary file while being reached
   through a *symlinked parent directory*. A loader callback that yields
   an unexpected source outside the selected mod layer must not cause
   the diagnostic tool to read arbitrary local files.
2. With more than `MAX_CONFLICTS` collisions, detailed rows were intentionally
   truncated, but the reported gameplay-critical *count* was computed
   from that truncated list. The total could therefore understate risk.

## Code

`yt_launcher_mod_conflicts_v232.py` now checks each source path against its
selected layer, rejects symlinks in every relative path component, and
also checks the resolved destination stays inside the selected layer.
The same check is repeated before optional content fingerprinting.

The gameplay-critical collision count is accumulated over **all**
enumerated collisions. Only detailed report rows remain bounded
(`MAX_CONFLICTS=4000`). The `conflicts_truncated` flag remains explicit.

## Source-only regression tests

`test_yt_launcher_mod_conflicts_v232.py` adds:
- injection of a source file outside its selected mod layer; expected rejection;
- 4002 synthetic conflicting gameplay targets from two selected mods;
  expected 4002 critical collisions, 4000 detailed rows, truncation=true.

Existing tests still cover precedence, base overlay, disabled mods,
case-folding, gameplay fingerprint changes, and read-only operation.
The `yt-v232-launcher-mod-preflight.yml` workflow tests against
the actual pinned upstream `bbport/scripts/mods.py` on Windows and Ubuntu.
A merged/released gameplay or launcher integration is **not** claimed by
these changes. CI outcome must be checked separately for the latest commit.

## Limits

No retail Bloodborne files, mods, saves, private chat screenshots or
production server credentials are uploaded. The preflight does not merge
DCX/BND archives, validate all game hooks, certify save compatibility,
measure networking performance or establish real Direct P2P. It is not
yet wired into the production launcher. Fornex is unaffected.
