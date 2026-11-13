# Native startup V413: first ordered retail run

The owner-private Linux run reached a new milestone: **88 consecutive
constructors returned in retail execution order**, beginning at constructor 1.
This is a controlled startup harness, not a desktop game executable.

## Evidence and trust boundaries

* The private input matched the pinned original 1.09 identity. GitHub Actions
  built only the public tools, from bbrecomp 8f31ec7 plus the existing V196,
  V199, V200, V201 and V203 patches. The image was read in the private worker,
  not supplied to GitHub, any public CI job or an upstream service.
* The real scanner found 241,821 function rows. The emitter produced 241,031
  generated function registrations in 383 C shards. The 790 exclusions were
  130 callers of setjmp-family imports and 660 import stubs. All 18,443
  constructor targets matched a row in the generated table, as checked by
  V410 against the local image, scanner and source manifest. This proves
  registration presence, not that all those rows can run without fallback.
* The private test executable used 94 generated functions whose table
  identities matched the whole-image table, plus the V388/V390 mediated
  memory layer and the V412/V413 host services. Only a bounded set of
  startup memory, relocation slots and process state was prepared. It did
  not run the retail process entry or a complete loader.
* Constructor 1 returned to the harness's supplied return address after 18
  attested host calls: two guard pairs, two recursive mutex setup sequences,
  one lock/unlock pair, zero-fill, and the size/allocate/map sequence for its
  116 MiB direct-memory arena. The postconditions include the game-visible
  mapping, initialized allocator object, two initialized mutexes, release of
  the outer lock, and intact return stack. Constructors 2–88 returned from
  genuine generated functions against the same VM; 3 initialized new objects,
  and 84 preserved objects already initialized through a shared guard.
* Optimized Clang, optimized GCC and Clang ASan/UBSan all passed privately
  on Linux AMD64. The native test binaries ran from a directory containing
  only the test executables; they do not read the PS4 executable at runtime.
  Unsupported STEP/TAIL/BAIL and unknown host calls are fatal in the test.
  The real 88-constructor run has not been done on Windows or macOS; those
  hosts passed the separate public fixture tests for the ABI adapters.
* The generated retail source, private callsite plan and test executables
  remain owner-private. This branch contains host adapters, tests, an
  original-free build-tool workflow and this aggregate evidence, not a
  runnable retail package or the private harness configuration.

Next frontier: ordinal 89 starts a different initializer, uses the existing
guard/mutex families, and goes beyond the admitted range into further
indirect dispatch and allocator-dependent state. Do not assume it can run
merely because its function is registered. Establish that path with actual
data dependencies and run it against the retained state of ordinals 1–88.

## Release gates for the independent PC build

| Gate | Required evidence before calling it shipped |
| --- | --- |
| Native startup | Ordered retail constructors and real process entry reach main without runtime EBOOT or translator; verify unsupported instruction/import paths, TLS and shutdown on each platform. |
| Offline game and settings | Boot to menu, load a save, transition maps, play/finish representative fights; test save compatibility, rollback, input remapping/chords, dedicated jump, device hotplug and display modes. |
| Rendering and performance | Capture visual parity and timing on fixed routes. Compare CPU/GPU frame time p50/p95/p99, stalls, peak memory/VRAM and cold/warm shader cache. Verify each upscaler and latency feature on supported hardware before enabling it. |
| Online, client and server | Separate session/control traffic from time-sensitive state; test packet loss, jitter, reordering, reconnect, host/server restart, save/progression integrity and mixed versions. Measure RTT separately from simulation and transport queueing; WAN zero latency is not a target. |
| Launcher and release | Separate native and compatibility builds. Versioned settings, clean upgrades and rollback, secure artifacts, crash diagnostics without retail data; publish only tested capabilities. |

References for comparison, not merged dependencies: bbport Windows forks
(Supermedo and Mrsuss60) for launcher and input/graphics behavior; shadPS4 for
ABI reference; pinned bloodborne-recomp for code generation; Khronos Vulkan
pipeline cache samples for warm/cold stutter measurements; SDL3 for device
input; GameNetworkingSockets as a transport candidate, not a replacement for
game replication or server authority. Keep Yharnam Together's separate
playable compatibility track out of the native startup result.
