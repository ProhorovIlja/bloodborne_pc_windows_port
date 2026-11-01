# Native V204: PRIVATE full original Bloodborne 1.09 image to Windows-native COFF

V204 connects the ACTUAL original source recompiler's full-image preparation
stages to our Windows AMD64 offline compiler, not a fixed synthetic-function
proof. All game input and all generated code must remain on the owner's
private computer, outside Git. This is NOT a playable Bloodborne.exe.

## The seven actual full-image stages

Exact pinned upstream: bloodborne-native/bloodborne-recomp
8f31ec7c41f252730c6325d52647046baef7549f.

1. Original tools/recomp/ps4elf.py extracts the decrypted user-owned
   game executable to a build-only x86-64 ELF.
2. Original tools/recomp/pointers.py identifies real relative relocation
   targets and function/vtable code pointers.
3. Original out/recomp/scan uses true Zydis on the entire original code,
   including unwind data and missing leaf functions, to create the real
   functions.tsv index rather than manually enumerated addresses.
4. Original tools/recomp/imports.py maps imported function stubs and slots.
5. Original full out/recomp/bbrecomp generates every discovered function
   into recomp.c plus recomp_XXXXX.c shards (no snippets mode).
6. V202 audits *all* generated modules for step/call/tail/bail/trace
   callbacks; strict release mode refuses these remaining guest dependencies.
7. On native Windows, the V198 SHA-256-verified incremental clang-cl pipeline
   builds all generated original function shards as x64 COFF objects.
   Unknown guest callbacks may be tolerated only under explicit
   --research-only, never under strict native-ready mode.

Linux/WSL2 is needed ONLY to run the original generator at BUILD TIME.
The eventual Windows game executable must never load WSL, original
EBOOT, a guest ELF, an emulator, or a PS4 kernel at RUNTIME.

## Current original-game blocker

Connected private Google Drive under gungrain@gmail.com was checked
again: the user's Bloodborne CUSA03173 directory exposes dvdroot_ps4,
sce_module and sce_sys assets, and other copies of its assets, but no
eboot.bin, ELF or SELF named file was discoverable in the Drive metadata.
The original game's *assets* are not its executable code. No legitimate
full original 1.09 AOT generation can be performed in our tools until
the user-owned decrypted original executable is available privately.

The V204 manifest labels the actual game version as UNVERIFIED until
matched against trusted original 1.09 metadata, rather than
assuming any uploaded executable is necessarily 1.09.

## Private build instructions: Linux/WSL2 preparation

Start with a disposable, full, public upstream checkout at the pinned SHA.
From our own project checkout, run the following in the given order.
All game-derived output must go to a private folder OUTSIDE Git.

    git clone https://github.com/bloodborne-native/bloodborne-recomp.git upstream-recomp
    git -C upstream-recomp checkout 8f31ec7c41f252730c6325d52647046baef7549f
    python3 native/source-port/recomp-v194/patch_upstream_linux_generator_v196.py --upstream-checkout upstream-recomp
    python3 native/source-port/recomp-v194/patch_upstream_ret_flags_v199.py --upstream-checkout upstream-recomp
    python3 native/source-port/recomp-v194/patch_upstream_indirect_call_v200.py --upstream-checkout upstream-recomp
    python3 native/source-port/recomp-v194/patch_upstream_indirect_jump_v201.py --upstream-checkout upstream-recomp
    python3 native/source-port/recomp-v194/patch_upstream_fallthrough_v203.py --upstream-checkout upstream-recomp
    (cd upstream-recomp && CC=clang ./build.sh)

Then point the actual complete-game pipeline at the original decrypted
game executable. This example assumes a PRIVATE mounted Windows disk:

    python3 native/source-port/recomp-v194/prepare_private_full_game_v204.py --upstream upstream-recomp --eboot /mnt/d/PrivateInput/eboot.bin --work /mnt/d/PrivateNativeWork/BloodborneAOT

Preparation refuses missing or encrypted input, a mismatched source
revision, absent real scanner/compiler binaries, invalid function
index, paths inside Git checkouts, or a nonempty output directory.

The owner-only work folder contains full original source-analysis TSVs,
all generated C modules, and a SHA256-based preparation manifest.
On success the intermediate original ELF copy is deleted. On failure,
partial *private* artifacts may remain: do not publish them, and use
a fresh directory for retrying.

## Native Windows COFF stage

Use the same source-pinned original upstream source tree, including
genuine deps/include Zydis headers and the V195 Win32 native clock
adaptation on original src/recomp/rc.h.

Run in NATIVE Windows PowerShell, NOT WSL2:

    py native/source-port/recomp-v194/patch_upstream_win32_clock_v195.py --upstream-checkout D:\Dev\upstream-recomp
    py native/source-port/recomp-v194/compile_private_full_game_v204.py --upstream D:\Dev\upstream-recomp --work D:\PrivateNativeWork\BloodborneAOT --jobs 4

Default STRICT mode correctly rejects generated functions that still
call a guest runtime callback. To get PRIVATE original-function x64
objects for diagnostics with unresolved callbacks, opt in explicitly:

    py native/source-port/recomp-v194/compile_private_full_game_v204.py --upstream D:\Dev\upstream-recomp --work D:\PrivateNativeWork\BloodborneAOT --jobs 4 --research-only

That output is verified native Windows AMD64 COFF object code.
No game PE is linked, no game is booted, and legacy callbacks
are not magically removed just because individual functions compile.

## Validation and limits

- Original full compiler source pin and runtime architecture researched
  and checked against latest upstream source and actual compiler pipeline.
- V204 tests cover source syntax, missing-private-original refusal,
  strict native runtime fallback rejection and research-only object
  compilation/reuse, on entirely invented original-generator functions.
- Real 1.09 entire-game preparation remains NOT EXECUTED because the
  original EBOOT is not accessible in connected Drive.
- A plain decrypted ELF may lack original PS4 module/dynamic metadata
  required by pointers.py/imports.py. Do not silently ignore
  failed import/pointer discovery and claim full function coverage.
- Full Windows imports, rendering, audio, threads, save/streaming,
  asset integration, executable linking and genuine game boot remain
  to be implemented and verified separately.

No game asset publication, PR merge, server/launcher updates,
Fornex deployment, or native release was performed. PR #84 is Draft.
