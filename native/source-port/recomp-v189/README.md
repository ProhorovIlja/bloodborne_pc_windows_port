# V189: first real Bloodborne 1.09 x86-64 leaf functions -> native C/Windows COFF

**Scope:** a *private, bounded proof of translating actual game instructions into independent native C*, **not** a full Windows Bloodborne game port. It does not reconstruct engine state, AVX, physics, event scripts, original PS4 imports or renderer. The final native game remains unbuilt. This stage is stacked on V187/V188 and keeps all game-derived outputs **private**.

## Source and what was actually verified

The user's original decrypted `eboot.bin` from private Drive is a genuine SCE ELF64/x86-64 and its **canonical loaded image SHA-256** matches clean Bloodborne CUSA03173 update 1.09 `071df19c8880086d97182dbc057bc8cb37badaca57d9112683836b24a0444c0a`. This reference hash is public in `lKaniel/bloodborne-server/bbport/scripts/game_check.py`.

The private probe parses the 162,959 `PT_GNU_EH_FRAME` function starts, verifies the full 91,042,036-byte image first, and selects **four distinct, tightly bounded** real executable *function entrypoints* (no branches, calls, memory, FS/TLS or indirect instructions). It recognises exactly four grammar forms: return zero, return 32-bit immediate, return 64-bit first argument, and return low-32 of first argument. It rejects any non-NOP instructions after their `ret` before the next function start and insists on 16-byte EH-frame intervals. **Selection is not dynamic or arbitrary emulation; all other function forms are deliberately unsupported.**

**Offline private proof executed 2026-10-31:**
- 416 scalar test comparisons via **actual original game instruction bytes** executed on the Linux x86-64 CPU in a temporary **W^X RX page** (instructions are copied ONLY after full clean-hash and whitelist validation), not through PS4 HLE or a CPU emulator.
- 276 scalar comparisons via generated **native Linux C** shared library loaded via the published bbrecomp `RcApi v4`-shaped ABI. The private test uses a deliberately small mock `BbCpu` layout, **not** complete ABI compatibility with the real upstream game CPU state.
- The same game-derived C was compiled into a real x64 **Windows PE32+ DLL** using V188 `clang-cl` COFF and `lld-link /EXPORT:bb_recomp_init`. Export present, 2 compilation units, actual file verified. **This particular private game-derived Windows DLL was not executed on Windows.**

Nothing derived from the game was copied into GitHub, public CI, a release artifact, or any publicly downloadable location. All private ELF, generated C, `.so`, `.obj` and `.dll` stay local. The source in this PR contains only a generic constrained parser/translator and **synthetic fixture tests**.

## Reproduce privately, with the user's own legal copy

On a Linux x86-64 host with Python 3.12 and clang:

```sh
mkdir -p /private/recomp-v189-generated
python native/source-port/recomp-v189/real_leaf_recomp_v189.py \
  --eboot /private/eboot.bin-decrypted \
  --private-output-dir /private/recomp-v189-generated
```

The script deliberately requires an **empty output folder**, verifies the clean game image and FDE table, compares original code to generated C on the native CPU, and writes only two **private** `recomp*.c` units. Console output is bounded counts/booleans and contains no game code, file paths, function offsets, register values or instructions. Do **not** upload the generated files.

On a Windows host with LLVM `clang-cl`/`lld-link`, compile those same private generated C units into a native DLL:

```powershell
python native/source-port/recomp-v188/win64_coff_link_v188.py `
  --source-dir C:\private\recomp-v189-generated `
  --include-dir native/source-port/recomp-v187 `
  --out C:\private\recomp-v189.dll
```

A fully independent Windows execution check of this exact **game-derived** DLL requires running on Windows with a private CPU ABI probe. **The public Windows CI instead generates synthetic toy functions** and executes them in a native Windows DLL. No private eboot or generated game code enters Actions.

## Gate status

| Gate | Status |
| --- | --- |
| Clean original game image + actual ELF function boundaries | PASS offline on private input |
| Four actual Bloodborne instructions/entrypoints -> machine-checked scalar C | PASS on Linux |
| Four actual game C functions -> Win64 COFF + PE DLL export | PASS offline, not executed on Windows |
| Synthetic recompiled module -> execute on native Windows and Linux | CI required |
| Actual upstream complete `BbCpu` layout + generated game chunks | **NOT TESTED** |
| Game startup without PS4 ELF or PS4 runtime | **NOT IMPLEMENTED** |
| Real five-player online and secure P2P integration | **NOT IMPLEMENTED** |

Next: genuine, bounded nontrivial leaf/C++ functions with memory/SSE and repeated differential evidence; prove whole-game bbrecomp C generated locally compiles against exact ABI on Win64; native Win32 engine services/renderer rather than PS4 API compatibility; then reconnect game to YT/CLS server. Do not conflate local 4-leaf proof with a playable Bloodborne port.
