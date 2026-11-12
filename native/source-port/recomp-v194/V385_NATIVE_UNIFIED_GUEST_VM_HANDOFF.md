# Native V385 — unified bounded logical VM for AOT, 23 math imports and 2 clocks

Date: 2026-11-12. On draft V384 PR #114. Scope: original-free source tests, actual V245/V384 Windows native RcApi registration and C11 host VM mapping, **not** a completed independent Bloodborne game.

## Real change
V384 already finalizes original V245 -> V226 math -> V239 clock -> synthetic `bb_recomp_init` native AOT table -> V381/V382 strict native-only CALL/TAIL, but V226/V239 guest import handlers still directly use host-aliased raw pointers. They cannot safely accept V383's logical guest addresses.

V385 adds `native_guest_vm_v385.{h,c}`, an explicitly pinned logical guest-address mapping backed by the V383 C11 atomic 64-bit words. The same logical addresses now serve AOT native return/push and the final imported math/clock callback. It allows 1,2,4,8-byte little-endian reads/writes within one word, using release/acquire stores/loads and C11 CAS for subword writes, no raw guest pointer dereference. A scoped V383 lease pins the mapping across import validation + the host math computation + both potential memory commits. Closing blocks new leases, but existing pinned operations finish before the owner joins all users and frees backing.

It also adds `native_unified_import_v385.{h,c}` that installs ONCE on the actual V245 registered `RcApi` pointer after V384 native-only finalization. It verifies the exact 23 original V224 descriptor names, handler identity, distinct offsets, 2 clock targets, and SAME memory backing as V382 native call route. It routes all recognized 23 imported math functions, including frexp/frexpf exponent-output writes, plus 2 Windows clock imports directly through V385 logical memory. Unknown targets are delegated to V384's already published native-only compiled AOT dispatcher, whose unresolved functions abort instead of invoking a translator. `step`/`bail` retain V381 fail-closed traps. No guest interpreter, EBOOT/SELF/ELF loader or commercial assets are linked into these public fixtures.

Return address writes are bounded by the mapped guest stack with atomics. frexp output/return collision, invalid pointers, unmapped addresses, closed memory and unknown opcode are explicitly rejected without CPU/guest memory change. The diagnostic `shyt_unified_import_try_v385` returns +1 handled, 0 unknown, -1 recognized unsafe. The published final RcApi callback aborts on -1; it does not forward unsafe known imports into the old raw-pointer handlers. Calling older V226/V239 wrappers directly is outside this new contract and must be removed or migrated before real release.

## CI
- `test_native_guest_vm_v385.c`: x64/ARM64 cross-platform atomic 1/2/4/8, same-atomic-word concurrent subword CAS, bounds, pin/close, invalid width, no-write-on-failure, no runtime original game data.
- `test_native_unified_import_v385.c`: genuine pinned public upstream headers and Windows V245/V384 callback bootstrap, known 23 math imports and 2 clocks with the SAME guest logical mapped stack used by native AOT CALL/TAIL; checks frexp denied unmapped/overlap and legacy host-alias stack not called.
- `.github/workflows/native-v385-unified-vm.yml`: Linux GCC/Clang + AddressSanitizer/UBSan, macOS ARM64 host-only, Win64 clang-cl pure VM and pinned public-upstream Windows RcApi integration.
- Green checks must be verified from the FINAL PR head before claiming passed; no original retail game data may enter CI.

## Engineering limits / P0
One contiguous C11 atomic backing is NOT the original game VM. Subword accesses may not cross an 8-byte atomic word; memory allocation, paging, permissions, 16/32-byte SIMD accesses, TLB, write-watch, guest aliases and mixed plain vs atomic generated C access remain incomplete. Entire game needs true original layout and memory ordering validated in owner-only 1.09 private tests. The V245 legacy raw handlers still exist behind the new final route and must be migrated/removed to avoid bypass. Linux has no real V236 clock bootstrap yet, and ARM64 game code is not compiled.

P0 next: modular multi-region process-wide VM with real page permissions and pin/unmap exclusion, implement all original import handlers in it, AOT complete original 1.09 code/hashes, native game entrypoint and linker closure to standalone Windows PE32+ / Linux ELF64, then prove no PS4 guest runtime. P1: native Vulkan/D3D12 renderer, streaming, 60Hz physics parity and correct 120/240Hz display. P2: controls/KBM/gamepad/NG+/HUD/accessibility; P3: LAN/P2P/dedicated online/server/launcher and optional vendor graphics features on actually supported hardware. P4 native ARM64 macOS direct Metal or tested Vulkan portability; not Rosetta as strict native goal.

Preserve BBPort and BBSC Ultimate Yharnam Together playable track independently; no fake claims that synthetic tests are original game launch.
