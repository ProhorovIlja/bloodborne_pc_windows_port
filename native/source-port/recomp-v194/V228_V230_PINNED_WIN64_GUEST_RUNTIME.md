# V228–V230: Win64 guest allocation ownership and pinned native math dispatch

2026-11-01, draft native PR #84. Goal: a Windows-native Bloodborne.exe
that does NOT load the owner's original PS4 EBOOT **at game startup**.
The current work is still a set of native runtime components, NOT
a playable port. Proprietary original-derived code, addresses and
binary objects remain on the owner's private system.

## V228: observed race in old guest memory permits

V227 `VirtualQuery` verifies a writable page **at one moment** but
does not prevent another game thread calling `VirtualFree` or
`VirtualProtect` before a math operation writes to that page.

New `native_guest_arena_v228.{h,c}`:
- Owns an actual `VirtualAlloc` reserved+committed Win64 region,
  bounded to 128 MiB per test arena, initially PAGE_READWRITE.
- Creates one owner-approved V227 guest allocation window; a
  `VirtualQuery` check **alone** cannot authorize arbitrary process
  memory outside this window.
- Acquires an SRW **shared** lifetime lock for every successful
  per-thread pin; the checked `ShytGuestMemoryPermit` callback
  rejects unpinned threads, invalid pages, read-only pages and
  out-of-allocation pointers.
- Uses an SRW **exclusive** lock for all owner-managed protection
  changes and `VirtualFree`; those actions cannot complete while
  an import is pinned. Disallows nested pins, wrong-thread unpin,
  repeated creation and reuse of a destroyed arena.
- Uses GNU `__thread` for clang MinGW and MSVC `__declspec(thread)`
  for clang-cl to support both Win64 toolchains.
- Only supports **one owner-managed allocation region**; this
  does not cover every engine heap, stack or memory mapping.

Real Windows CI ran `VirtualAlloc`, `VirtualProtect`,
`VirtualQuery`, two concurrent Win32 threads, reader pin and
exclusive-destroy contention. It proved `VirtualFree` remains
blocked until the active reader releases its lock, and that the
stale window cannot allow access after destruction.

V228 GitHub CI **SUCCESS**:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41332102959

## V229: pin the entire actual RcApi V4 math call

Modified `native_math_rcapi_route_v226.{h,c}`:
- Added mandatory memory `pin_enter`/`pin_leave` callbacks to the
  new `shyt_math_rcapi_route_v226_install_pinned` entry.
- The old `shyt_math_rcapi_route_v226_install` entry is disabled
  and always returns failure. This prevents *new* unpinned
  dispatchers from being installed accidentally.
- Holds the memory pin during the **entire V224/V223 math import
  evaluation and return-stack update**.
- Releases the pin BEFORE calling a guest fatal callback that may
  `longjmp`, or delegating an unknown target to the original
  `RcApi.call`. This avoids pin/lock leaks across error unwinds.
- A failed pin enters the fatal guest error path instead of
  touching guest memory.
- Updated original pinned BbCpu/RcApi synthetic tests assert
  matching enter/leave counts and absence of a held pin inside
  fault/old callback, including denied-pin cases.

New `native_math_arena_route_v229.{h,c}` installs the V228
Win64 allocator as the concrete V226 pinned route, with a
lifetime-locked V227 page permit. It is compiled as real
AMD64 Windows COFF with public pinned upstream BbCpu:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41332102764
**SUCCESS**. No owner-derived game address table is published.

## Actual full-game code compilation continued

The private V213 full original AOT source remains **384** C files,
with 241,031 registered AOT functions and a separate unresolved
1,468,066 static guest fallback calls. Two new original generated
source shards `recomp_0001f.c` and `recomp_00057.c` compiled via
V219's bounded incremental Win64 cross-compiler.

The private SHA-256 manifest now shows **54/384 real original
Windows COFF objects**, total **246,019,772 bytes**, with **54/54**
matching recorded file sizes, SHA-256 hashes and AMD64 COFF machine
identifiers, 0 mismatches. **16** objects carry the stronger V219
dependency-tree compiler/SDK fingerprint; 38 historical objects
are byte-verified but require revalidation under the newer cache
rules before reuse.

## V230: real native Windows runtime execution test

Added `test_native_math_arena_route_v230.c` and the public-only
GitHub workflow `native-v230-windows-guest-math-exe.yml`.
It builds a real Windows PE EXE using the pinned public original
`BbCpu` and `RcApi` definitions, public V222–V229 native source
and generated public Zydis dependencies. No EBOOT, retail game
C, graphics assets or original import offsets enter public CI.

The fixture uses INVENTED import offsets and an owned guest
allocation to test `pow`, `frexp`, old callback fallback,
read-only return-slot refusal, read-only output pointer refusal,
`longjmp` fault handling after releasing the lifetime pin,
and failure after arena destruction.

**V230 SUCCESS:** Both the public dependency-preparation job and
actual Windows PE execution job passed:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41332349835
This test fixture is not Bloodborne gameplay nor a full game launch.

## Still missing

- A full Windows-native game memory manager to own guest
  allocations and register actual original game regions.
- A proper guest fatal-error boundary and integration of the
  V229 route into the full original game's `bb_recomp_init`.
- Full linking of 384 generated AOT modules, host imports, all
  Windows services and removal of guest CPU fallback dependencies.
- Renderer, audio, asset streaming, input, saves, network,
  game initialization and first authentic Bloodborne Windows boot.
- Continuous stress tests and save integrity, not only synthetic
  register tests.

No Fornex production changes, no release, no merge.
