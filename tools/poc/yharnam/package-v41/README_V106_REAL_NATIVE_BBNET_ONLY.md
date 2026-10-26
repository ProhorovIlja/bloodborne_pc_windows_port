# V106: real original Yharnam Together game C++ without 165-minute GPU render build

2026-10-26. DRAFT PR20, pinned original `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`. Not deployed to production. Neither original Qt shadNet nor saved games, accounts, GPU libraries nor multiplayer data packets are modified by this diagnostic mode.

## Why

Previous CI for V97 Doll menu, V98 lamp respawn and V99 revived boss AI tested the actual pure C++ policies on Windows and Ubuntu and V101 staged seven original patched game files into the PR20 Windows build. However, those tests did **not** prove that the full native `bbnet` static library compiles with the actual Windows Clang64 ABI and original CMake dependencies. Full native GPU builds frequently take 165 minutes and are still queued/in-progress.

## Actual implementation

- `patch_bbnet_only_v106.py` applies **only after V103** to the exact original pinned `bbport/build.sh`. V103 already requests `ninja -C out/gpu bbnet` before GPU, so V106 adds a **strictly opt-in** `SHYT_BBNET_ONLY=1` branch immediately after that real Ninja target: require a nonempty `out/gpu/libbbnet.a`, report `SHYT_V106_REAL_NATIVE_BBNET_ONLY_COMPILED` and exit successfully before building `bb-probe`, `bb-gpu-capabilities`, `bb-play` and any package. Default `SHYT_BBNET_ONLY=0` leaves the ordinary complete Windows build and game packaging unchanged.
- `test_bbnet_only_v106.py` validates the exact V103 source anchor, one genuine `ninja ... bbnet`, correct location of the optional exit, intact normal GPU command, refusal of repeated patch or drift.
- The existing real pinned workflow `.github/workflows/shyt-v36-composed-windows-client.yml` exposes an optional `workflow_call.inputs.bbnet_only` boolean. `env.SHYT_BBNET_ONLY` passes it into the ordinary CLANG64 MSYS2 build. The same **original game's** V95 UI/BL, V96 Vulkan launcher, V100 Sirit, V101 game patch/source digest and V103 source stages are applied. Its real build step requires `libbbnet.a` if in bbnet-only mode instead of demanding unbuilt EXEs.
- All full-game package, ZIP, stamping, checksum and public release checks are **skipped in diagnostic mode**. A small internal-only 7-day evidence artifact carries `libbbnet.a`, `bbnet-build.log` and the exact V101 seven-file SHA-256 manifest; no legitimate game assets, private peer keys, accounts or save files.
- To avoid duplicate heavy Windows runners, **the existing verified `.github/workflows/shyt-v103-game-bbnet-before-gpu.yml`** now first runs the V103/V104/V106 narrow source guards on Windows + Ubuntu and then runs its **single** `compile-real-original-game-bbnet` job through the SAME original reusable real Windows pipeline with `bbnet_only: true`. The redundant newly added standalone V106 workflow was removed before running duplicate full toolchains.

## Clear limits

The narrow source regression test is **not** the Windows bbnet binary compilation. The latter is verified only if the real V106 Windows job finishes successfully and the attached internal artifact actually contains the static library and hash manifest.

Even a successful `libbbnet.a` does NOT prove GPU renderer C++, native Windows EXE, archive, gameplay, original server interop, BL/Discord RPC, Save/Restore, player death or boss AI in a two-PC game. Native encrypted Direct gameplay P2P remains OFF and no server-load gains are claimed.

Original full Windows workflow stays available and independent. Fornex, CLS Friends, master, accounts, saves and production firewall unchanged, all branches DRAFT.


## V108: verify actual linked-in gameplay translation units

A nonempty `libbbnet.a` is necessary but not sufficient evidence that the
V97–V99 game sources reached the real native static library. V108 adds a
**diagnostic-only post-compile gate** to the same original Windows workflow,
after the real `bbnet` Ninja step and before the internal-only evidence upload.

`verify_bbnet_archive_v108.py` calls `llvm-ar t` on the built archive and
requires **exactly one** object member each for
`bloodborne_re.cpp`, `bloodborne_party.cpp`,
`bloodborne_party_death.cpp` and `bloodborne_flags_store.cpp`.
It also checks the pinned upstream revision, development-only and Direct-OFF
settings in the V101 manifest, then recomputes SHA-256 of all seven patched
original-game source files. Missing/duplicate objects, source drift or
unsafe/malformed manifest fields reject the build.

`test_verify_bbnet_archive_v108.py` exercises the validator against explicit
positive, missing, duplicate, empty archive, source tamper and unsafe manifest
fixtures. It runs in the existing V103 Windows/Ubuntu source-test matrix.
The *real* archive verification runs only after actual Windows Clang64 C++
compilation. The ordinary full-game workflow remains unmodified by this
extra diagnostic gate, and the new checks do not claim a playable EXE.

### V107 CI queue behavior

The V103/V106/V108 diagnostic caller coalesces superseded **pending** runs
for the same feature branch using a dedicated concurrency group with
`cancel-in-progress: false`. Already-running compilers are not cancelled.
The complete GPU/EXE workflow retains its independent scheduling.
