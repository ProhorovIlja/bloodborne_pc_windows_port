# V227: real Win64 guest memory validation and original-code COFF continuation

Date: 2026-11-01. Native draft PR #84, user target: an independent
Windows Bloodborne executable with NO original PS4 EBOOT required
at game launch. All original-game-derived code remains private.

## Concrete unsafe import fallback corrected

The V226 checked math dispatcher previously returned status 0 (unknown
target) prematurely when `next == 0`, `cpu == NULL`, or the guest-memory
validator was missing. That could send a **recognized and unsafe**
original import into the old `RcApi.call` fallback. This is fixed:
**a recognized target always yields -1 if any required context/return
address/checker is invalid**, and the V226 route calls its mandatory
fatal guest fault callback. An unknown target still delegates to
the original handler with unchanged CPU state. Updated the V224
negative tests for zero return address, missing validator, and
missing CPU. The unchecked V224 entry remains disabled.

## New actual Windows host guest-memory permit

`native_guest_memory_v227.{h,c}` defines an immutable, explicit
allowlist of at most **32 disjoint sorted guest allocation windows**,
each a nonzero half-open [start, end) range. It refuses invalid
windows and checks every requested address span (up to 4096 bytes)
using overflow-safe arithmetic.

On **Windows x64**, `shyt_guest_memory_v227_permit` first requires
the entire requested write to fit **one registered guest window**,
then calls actual Win32 `VirtualQuery` over **each part of the
requested range**. Only committed, writable, non-GUARD,
non-NOACCESS pages pass; copy-on-write pages are considered writable
when their page type is a recognized Win32 write/COW type.
Read-only, uncommitted, released, guarded and out-of-allowlist pages
are denied. On Linux/other hosts, the Windows adapter deliberately
fails closed rather than pretend it knows host page permissions.

The future native loader must register the actual still-live guest
stack/heap/IO allocations as windows before issuing `RcApi.call`,
and guarantee no competing thread unmaps or changes their protection
while an import executes. **VirtualQuery is a point-in-time check**
and cannot guarantee safety against an unrelated concurrent
VirtualFree/VirtualProtect. The loader/allocator lifecycle lock or
pinned regions are still necessary.

### Actual public Windows runtime tests

`test_native_guest_memory_v227.c` directly uses:
- `VirtualAlloc` to commit three pages and register their range;
- `VirtualProtect` to turn the middle page READONLY and PAGE_GUARD;
- a write spanning a writable-to-readonly page boundary;
- `VirtualFree` to ensure the old registered range alone never
  authorizes released host memory;
- out-of-range writes, overflow, oversized requests, invalid sorted
  overlapping windows and non-write permissions.

**All Windows 2022 native tests and Linux fail-closed tests PASS:**
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41329691683

The changed V224 semantics initially caused the prior regression
test to expect 0 instead of -1 for an invalid zero return address.
Updated the test to assert the safer contract and added null
CPU/validator cases. Reran original pinned `BbCpu`/RcApi tests:
- V226: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41329797762
- V223/V224: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41329797749

Both PASS after the fixture was updated. No raw job logs downloaded.

## Actual proprietary original-game C/COFF progress

Verified the existing private V219 manifest at **50/384**
actual generated C modules (all with source from the owner's original
decrypted CUSA03173 Bloodborne). Using the bounded 45-second
V217/V219 compilation tool, compiled two further DISTINCT original
modules `recomp_001b6.c` and `recomp_00265.c`.

The resulting PRIVATE manifest now contains **52 actual AMD64 Win64
COFF objects**, total **239,274,689 bytes**, with **14 objects**
carrying the stronger V219 full header/compiler dependency hash
and 38 historical objects still requiring revalidation if reused.
Independently rehashed all 52 with SHA-256, checked exact byte
lengths and 0x8664 AMD64 COFF headers: **zero mismatches**.
No original game source/ELF/addresses/COFF objects uploaded.

## Incomplete, not to be overclaimed

- The V227 allowlist is a library, **not yet populated** by a complete
  Windows Bloodborne allocator or memory manager.
- No real in-game thread yet installs the V226 `RcApi` route with a
  V227 permit plus a complete fatal guest fault boundary.
- 52 individual Windows COFFs are not a linked Windows EXE. The
  full original 384-source build and native import/service runtime
  remain incomplete.
- V216 measured **1,468,066** static guest callbacks throughout
  generated original C code. V225's 1,089 statically identified
  named direct math calls are not a substitute for replacing the
  remaining guest callbacks, and indirect calls require separate
  runtime routing.
- Guest numeric FENV/errno, graphics, audio, input, saves, network,
  assets, native game init, actual runtime memory mappings and first
  independent no-EBOOT boot remain to be implemented/tested.

Fornex production untouched, neither PR merged, and no private
game files or WIP Discord material published.
