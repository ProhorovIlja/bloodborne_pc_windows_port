# Native V388 — OS-backed multi-region pages, protection, cross-word operations and actual Win64 RcApi fixture

Date: 2026-11-12. Based on draft V387 PR #117 and all earlier synthetic native P0 code. This is actual original-free source/test infrastructure, not a playable independent Bloodborne PC release.

## Native host page backing
`native_os_vm_v388.{h,c}` owns caller-licensed, freshly allocated system memory pages:
- Windows AMD64: `VirtualAlloc(MEM_RESERVE|MEM_COMMIT, PAGE_READWRITE)`, `VirtualProtect`, `VirtualFree(MEM_RELEASE)`.
- Linux AMD64 and macOS ARM64: private anonymous `mmap(PROT_READ|PROT_WRITE)`, `mprotect(PROT_READ` or `PROT_READ|PROT_WRITE)`, and `munmap`.
- All pages are rounded to the actual OS page size, aligned and initialized using C11 `atomic_init`, NOT zero bytes assumed to be initialized atomic objects. V386 registers each guest logical address range and owned atomic backing as an immutable region, enforces no aliasing or overlap, checks W^X and permissions; V388 seal applies physical OS read-only protections to guest non-writable regions. Guest EXECUTE is intentionally only *metadata*: native guest code cannot execute allocated backing; we do NOT make writable memory executable.
- Guest W-only logically denies reads via V386/V388 even though underlying OS page may be RW (Windows does not provide a portable write-only protection class).
- On shutdown, close refuses new leases and allows active ones to drain; release explicitly requires quiescent VM AND caller affirmation that all owner worker threads have been JOINED. OS unmap occurs only after this. Published RcApi routes or callbacks cannot outlive mapped guest backing; the Windows full-route fixture intentionally lets OS reclaim lifetime backing on process exit.

## Cross-word guest data
`shyt_native_os_vm_read/write_v388` allow guest little-endian widths 1,2,4,8 that cross an aligned 64-bit backing-word boundary as long as both words are in the SAME guest region/OS allocation and the permissioned pinned lease is still held. They reject cross-region (even physically/guest-address-adjacent), unmapped, invalid width, permission-denied and address overflow before writing anything. Each word uses C11 atomic load/store/compare-exchange; crossing a word boundary is TWO separate atomic operations and **the entire crossing operation is NOT one atomic transaction**. Other V386 paths can interleave, so no full x86-64 CPU memory parity is claimed. 16/32-byte SIMD and atomic guest x86 LOCK operations still require explicit implementations.

`shyt_native_os_vm_stack_write_v388` is a direct V382 native-only guest CALL stack writer. Return address is checked as a logical address, not dereferenced as an unsafe host pointer.

## Tests
1. `test_native_os_vm_v388.c`: synthetic V381 attested AOT -> V382 native-only CALL/TAIL using real OS-allocated and protected memory, OS page alignment/allocation/permission checks, adjacent guest-region crossing denial, unaligned 2- and 8-byte cross-word little-endian operations, invalid/unmapped/read-only/write-only address handling, no mutation on invalid access, concurrent byte CAS (Unix), original-free close/pin/join/release test. No original retail AOT or private game code.
2. `test_native_os_bootstrap_v388.c`: Windows-specific proven V245/V384/V387 pinned *public* upstream RcApi-v4 chain, but the 4 V386 guest regions are now ACTUAL `VirtualAlloc` allocations instead of C11 stack arrays, and physical read-only protection is checked with `VirtualQuery`. Two synthetic RcFn native functions, 23 math and 2 clock import routes, cross-region `frexp` writes, R/W permission failure, and native CALL/TAIL remain checked. The published strict route keeps its OS memory alive until process termination.
3. `.github/workflows/native-v388-os-backed-vm.yml`: Linux GCC/Clang + ASan/UBSan, macOS ARM64 host-only, Windows AMD64 clang-cl isolated OS memory test and pinned public upstream Windows full RcApi integration. CI success requires actual job-log confirmation at latest head.

## Engineering boundaries
- V388 provides OS-owned PAGE allocations and lifetime/protection for a bounded static multi-region array. It DOES NOT map original game address space into those identical host virtual addresses, handle region aliases, the original game's generated C memory model, DLL imports, OS file mapping, page faults, dynamic region mprotect/reload/remap under active game threads, guard pages, full original CPU instruction semantics, GPU DMA, process-level exceptions/SEH, or game saves/shaders.
- V386 max 32 regions / 1,048,576 64-bit atomic words each remains inherited; the original game will need more flexible page tables, memory slabs, VRAM host synchronization, and legal owner-only assets.
- Original game AOT function closure, **all** host imports, the original game entrypoint and truly independent Windows PE32+/Linux ELF64 executable boot remain unproven. An original-free two-function native test is not the game.
- macOS ARM64 host compilation is not ARM64-native Bloodborne compiled game nor Metal renderer; Windows QPC V239 math/clock bootstrap is still Windows-only. Game playable/online/performance and user QoL remain major later work.
- OS host backing is still memory storage only, not a guarantee of no runtime PS4 ELF/translator in a REAL original-game executable. The final independent game boot must be privately observed with appropriate process tracing and fully legitimate game content.

## Next
Check final V388 CI and repair real errors. Next V389: page-aware dynamic mapped allocations with OS-level remap/protection under leases and better cross-word operations, robust original-game memory faults and source-generated memory adapters, Linux native clock route and original game import closure. Eventually entire original-game 1.09 native executable/renderer/gameplay, stable 60Hz+ rendering with simulation parity, DLC/chalices/saves, client/server/online/KBM/launcher settings. Keep playable BBPort/BBSC Ultimate separate. Never upload original Bloodborne/DS3 licensed bytes or credentials to GitHub/CI.
