# Native V386 — sorted permissioned multi-region guest VM + native CALL/TAIL

2026-11-12, based on V385 draft PR #115. No original-game files/assets or owner-private code are included.

## Source
`native_multi_region_vm_v386.{h,c}`: maximum 32 immutable guest regions, each caller-owned initialized `_Atomic(uint64_t)` array with explicit guest base, word count and guest read/write/execute permissions. Maps logical guest addresses to memory by O(log N) region binary search, then bounded index. Registration requires single-threaded zeroed VM, aligned and nonzero addresses, valid word counts, no guest-range overlap, no host backing alias overlap, no address overflow, W^X, and no modifications after seal. Guest address is NEVER interpreted as host pointer.

Permission enforcement: reads require R; writes require W; an EXECUTE flag is only access metadata and NEVER executes any code. Windows PE/ELF executable pages and native AOT code are separate future concerns. W^X is enforced here even before OS page-protection APIs exist.

Memory operations: little-endian 1/2/4/8 bytes within a single 8-byte C11 atomic word. Subword writes use compare-and-exchange, full-word stores use release and reads acquire. Width and region-boundary crossings fail closed and DO NOT mutate backing. **This is NOT sufficient for real mixed-size/cross-word original-game VM.**

Lifecycle: immutable regions and C11 atomic pin count plus irreversible closing bit; all pins rejected after close, existing pinned transactions allowed until quiescent. The caller MUST additionally join all threads before freeing VM/state/backing. This module does not allocate OS virtual memory, change mprotect/VirtualProtect, handle true OS page faults, map original game assets, or prove data-race freedom for generated native AOT code that uses non-atomic direct memory.

`shyt_native_vm_stack_write_v386` directly matches V382's native-only AOT CALL/TAIL stack-write callback, so bounded guest function dispatch can now choose among multiple regions, requiring W in target stack. Same native VM supports guest reads, including return address pops.

`test_native_multi_region_vm_v386.c`: four unsorted registered regions (read-only, read-write data, write-only, read-write stack) sorted on registration. Checks invalid/overlapping guest or host address ranges, W^X rejection, sealed immutability, guest and host overflow, read-only/write-only behavior, word-crossing rejects, atomic little-endian subword updates, Unix concurrent writers to distinct bytes of same word, lease/close/quiescence and revoked new pins. A second real V381/V382 synthetic AOT table executes native C CALL and TAIL through the V386 stack backing (no interpreter), and tests missing AOT targets and closed memory.

Cross-platform CI: Linux GCC/Clang/ASan/UBSan, Windows AMD64 clang-cl, macOS ARM64 host-only. CI green proves only this portable C11 contract on synthetic code, not native original Bloodborne boot.

## Relationship to V385

V385's FINAL Win64 23 math + 2 clock import dispatcher still accepts `ShytGuestVmV385`, a ONE-REGION abstraction. V386 does NOT silently change that production-looking API; callers must not pass a V386 VM pointer where V385 VM is expected. V386 confirms multi-region permissioned memory and native AOT stack integration; a later change must explicitly generalize V385 imports to a callback-based interface without permitting raw host-pointer fallback, preserve proper V245/V384 bootstrap and original-game return semantics.

## Remaining genuine native port blockers
- Unified VM needs dynamically allocated game regions, actual OS page permissions, multi-region/cross-word read/writes, unaligned guest machine semantics, aliases, executable mapping for own compiled code, and correct access with any original generated AOT C memory paths; atomic/plain mixing must be resolved.
- Original Bloodborne 1.09 function table and ALL import stubs, patched instructions, setjmp and dynamic dispatch remain unverified. Owner-only full AOT source compilation, native host import ABI, full Windows PE32+/Linux ELF64 linker closure and real OS boot trace WITHOUT PS4 guest executable/translator required.
- Renderer and shader parity, textures streaming/VRAM/vertex cache, physics fixed-step across 60+ display, DLC, bosses, saves and QoL, stable online/LAN/P2P/dedicated client/server/launcher and supported upscalers/HDR/VRR remain independent major work, NOT accomplished by V386.
- Apple Silicon host compilation isn't a native ARM64 original-game port.
- Preserve BBPort and BBSC Ultimate Yharnam Together playable track separately. Never distribute original game/DS3 copyrighted assets, credentials or private original code on public GitHub/CI.
