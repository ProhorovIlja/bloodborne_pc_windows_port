# V220, 2026-11-01: native Bloodborne imports vs BBHost public runtime

This report uses **real PRIVATE decrypted CUSA03173 Bloodborne 1.09** only
in the local container; no original ELF, imported symbol dumps, C
code, runtime objects, online credentials or screenshots are checked
into public GitHub. The reference BBHost Git commit was pinned to
`8d8f07db3bad61dcdbf11511c9d34acfdfa162cd`.
Source files consulted: `src/core/plt_names.inc`,
`src/core/imports.cpp`, `src/net/stun.h`, `src/net/session.h`,
`docs/online.md`, `docs/performance.md`, and GPLv3 license.
Repository: https://github.com/droogie/bbhost .

## Exact original build-time import-name comparison

- Real original full V213 `scan/imports.tsv`: **660 imported-stub rows**.
- Public BBHost `kPltNameCount`: **661 PLT ordinal rows**.
- **659** occurrences have the same import name between those tables,
  with all **659 in the same relative sequence**.
- 1 original scanner-import name is absent from BBHost's public PLT:
  `sceFiosFHSyncSync`. Its corresponding BBHost index is a **blank
  name**, not a stated implementation.
- BBHost adds `__tls_get_addr` (one extra nonempty entry).
- BBHost's second additional entry relative to the private scanner is
  the **empty placeholder** at the FIOS ordinal.
- Note the original ELF V206 relocation audit gives **661 jump slots**,
  **684 reconciled relocation slots**, and **23 global-data slots**.
  Counts differ because scanner import-stub rows and ELF relocation
  slots are distinct grains; no contradiction or automatic coverage
  assertion is justified by 660 versus 661.

The independent real original V206 import-family audit (not a native
implementation test) reported original imported-API families:
`win32_crt_kernel_time=321`,
`account_multiplayer_social=113`,
`windows_network_http_tls=67`,
`windows_gpu_present=58`,
`windows_audio_video_voice=48`,
`windows_asset_io_save_data=40`,
`windows_input_ime=18`,
`other_platform_services=19`.
These are coarse categories, not a complete OS API implementation plan.

### Important interpretation: symbol-name overlap is NOT native closure

`src/core/imports.cpp` BBHost `bind_import` uses `g_hle` if
registered, otherwise falls back to `hle_make_stub`. Matching a
PLT name therefore does **not** prove its host implementation exists,
is correct, is binary ABI-compatible, or works in game.

BBHost currently runs the original Bloodborne ELF and resolves its
imports into host implementations, translates graphics to Vulkan,
and supplies host network/audio/saves. This is a valuable architecture
reference, but by the user's explicit definition **not the completed
independent PC port**: the final native EXE must not load the PS4
`eboot.bin` at runtime.

Reusing logic from BBHost requires preserving its GPL-3.0 license
terms, not copying code blindly into code with incompatible licensing.
The first implementation target is independently validated PS4 import
wrappers and mapped native runtime services *after* COFF ABI/state
requirements are satisfied.

## Source-backed BBHost online observations

`docs/online.md` describes NP Matching2 matchmaking via server;
direct UDP on P2P port 9307 (subsequent local instance chooses another
available port); STUN/reflexive endpoint; peer NAT punchthrough;
server relay fallback. These are network architecture references,
**NOT evidence of interoperability with Yharnam Together**.
It explicitly says BBHost sessions contain BBHost players, not PS4
crossplay. BBHost describes five participants in selected late areas
with up to two invaders; not a blanket five-friends co-op guarantee.

`docs/performance.md` includes a stage-specific bottleneck meter:
main, GX workers, render, CP, record, GPU, present and stalls.
We should benchmark the native pipeline and future YT hybrid/P2P with
per-stage data rather than accept one person's qualitative FPS claim.

## Public reproducibility

`native/source-port/recomp-v194/compare_private_imports_bbhost_v220.py`
compares original private `scan/imports.tsv` to the public PLT file
by name and order, printing only aggregated results. It never prints
private addresses, original symbols or NIDs. Public Windows/Ubuntu
synthetic tests and pinned public BBHost table check all PASS:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41323435413 .
The PUBLIC GitHub CI contains ONLY public BBHost's GPL-licensed names,
license text and deliberately invented TSV test values; no user game.

## Native port next steps, not yet achieved

1. Inventory actual registered BBHost HLE functions, not only PLT
   names, and isolate **no-op stubs** from fully implemented imports.
2. Compare CUSA03173 native ABI signatures, data layout and TLS,
   implement Win64 native replacements with PS4 bindings only as
   build-time references, never a runtime original ELF loader.
3. Retain V219 content-addressed COFF-cache safety and compile
   remaining native modules. All 50 previously checked objects retain
   guest-runtime calls and do NOT prove standalone native game boot.
4. Remove measured guest `rc->call/tail/bail/step` dependencies,
   validate game init, graphics, audio, saves, input, network; test
   first no-EBOOT native Windows startup.
5. Keep private owner data and third-party WIP reports private.
   No changes to Fornex, no merges.
