# Native V197: actual whole-function recompilation into Windows PE32+ EXE

**Win64 and Linux CI passed. Real full upstream generator, synthetic-only
input. Not the game.**

[Verified GitHub Actions run 41252438814](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41252438814)
at revision `986ef83a4627a00be46f96eb3e04ebe365a721b1`.

## Why V197 matters beyond V196

V196 executed `bloodborne-recomp`'s original `bbrecomp --snippets` mode
for isolated invented instructions. V197 invokes **its normal whole-game
function compilation mode**, exactly as its real-game compiler does:
`bbrecomp ELF functions.tsv recomp.c @function_offsets.txt`.

The inputs are a **fully invented, bounded synthetic x86-64 ELF64** built
in CI, not the player's Bloodborne game code or any copied private
executable. The fixture contains five complete function bodies, each
ending in a real x86-64 `RET`, plus a call from offset `0x1030` to
`0x1050` with a genuine 32-bit PC-relative `CALL` displacement. It
has a valid ELF program header and a five-entry synthetic function table.

The original compiler uses **real Zydis v4.1.1**, emits the upstream
`RcFunction` table containing function start, length, exact hashed source
bytes, compiled C entry points, and writable direct-call dispatch slots,
plus the separate **actual** `recomp_00000.c` C function shard. No
hand-written replacement functions are substituted.

A separate source-checked compiler runner links `recomp.c`,
`recomp_00000.c` and our native host under the full original
`RcApi v4` and 840-byte `BbCpu` ABI into Linux and Windows EXEs.
The Windows EXE uses the original upstream C helper header with the
natively patched Win32 `QueryPerformanceCounter` clock, and a real
Zydis header set (not the V195 include-only stub).

On both platforms CI **actually invokes all five original-generated
functions**, checks guest `RAX`, `RIP`, `RSP`, source-hash table
presence, guest-return stack pop, and the inter-function direct
`CALL -> RET -> outer RET` path. The direct-call targets
are initialized from `RcFunction.direct` before invocation and
the callback table fails if native code ever falls back to
`RcApi.step/call/tail/bail/trace`. The host rejects a runtime
`--eboot` argument. No guest ELF loading, console OS, PS4 kernel
emulation or retail game source is required by the executable.

## Reproducible, publicly safe source-only pieces

- `generate_whole_functions_v197.py`: forms and compiles only
  invented ELF/functions; checks pinned upstream `bbrecomp.c` SHA,
  expected original C function declarations and direct-call dispatch
  sites, no output under a Git checkout.
- `bbrecomp_whole_function_host_v197.c`: native process entrypoint
  and five end-to-end semantic and return-address tests.
- `build_actual_upstream_win64_v197.py`: absolute Windows paths
  for clang-cl, source-locked actual `RcApi`, real upstream C units,
  native Win64 compilation/execution and rejected EBOOT argument.
- `.github/workflows/native-v197-full-functions-win.yml`: two-stage
  ephemeral Ubuntu compiler/Zydis job and Windows Server 2022
  native source execution. The only transferred CI artifact is
  **original-upstream-derived C from invented instruction bytes** and
  public Zydis headers, retained for one day.
- `patch_upstream_linux_generator_v196.py` and
  `patch_upstream_win32_clock_v195.py`: exact pinned and reviewed
  source-only portability adapters for the build host and platform
  helper, respectively. No upstream sources are overwritten in their
  own repositories.

## Major remaining obstacles before ANY playable Windows Bloodborne

1. **Compile original privately owned CUSA03173 1.09 game**, not
   a five-function synthetic ELF: full scan, 241k function set,
   return/flags/vector/call/interpreted-code coverage, original code
   hash checks and independent replay. Generated game C and Windows
   objects must remain private. We have **not** run this entire pipeline
   against the player's game for Win64 yet.
2. **Eliminate PS4-style runtime dependence:** original
   `bloodborne-recomp` emits `RcApi.step/call/tail/bail` for the
   unhandled instructions, indirect dispatch, import calls and
   translator fallbacks. V197 tests a subset where none are executed;
   it does not solve general fallback or platform imports.
3. **Direct Windows engine:** its own startup, memory/threads/TLS/SEH,
   native renderer from engine draw state rather than PS4 GNM
   emulation, asset world streaming from private game/DLC data, native
   input, audio, media, physics, events and save compatibility.
4. **Real-game acceptance:** Windows 10/11 clean install, the entire
   offline campaign, Old Hunters, chalices, all endings, NG+,
   cutscenes and sustained stability/performance, with absolutely no
   EBOOT/PS4 executable read at process runtime.
5. **Secondary features AFTER offline playability:** multiplayer
   engine/secure P2P/native server, five total co-op/invasion seats,
   friends, inviting, QoL and native installer/launcher. No
   Yharnam Together/PS4 compatibility runtime should silently become
   the final program.

## Source review and licensing

The source-locked original upstream
`bloodborne-native/bloodborne-recomp@8f31ec7c41f252730c6325d52647046baef7549f`
is **GPL-2.0-or-later**. Zydis is MIT licensed. Any reuse,
linking, binary distribution or third-party code combination must
respect licenses and distribution constraints. Original game content
must never be bundled with this repository.

No user game data, Fornex deployment, merge or production process
was affected. See
[NO_EBOOT_WINDOWS_NATIVE_TARGET.md](../NO_EBOOT_WINDOWS_NATIVE_TARGET.md).
