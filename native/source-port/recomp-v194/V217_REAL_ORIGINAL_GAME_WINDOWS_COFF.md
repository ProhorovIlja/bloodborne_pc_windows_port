# V217: real original Bloodborne full-image Win64 COFF cross-compilation (2026-11-01)

## Actual private result

The V213 original decrypted-game full scan and patched AOT generator already
produced **241,821 scanned functions**, **241,031 registered AOT entries**
and **384 generated C source files, 1,585,909,087 bytes**. Exact registered
address/size parity was independently checked with V207. The full
source set still has **1,468,066 static fallback callbacks** (V216), so
strict native-only runtime is NOT ready.

The first V214 MinGW public SDK artifact was **NOT portable**: 1,630 header
files were symlinks into the GitHub runner's /usr/share/mingw-w64. Only
three files were regular. This was discovered by inspecting the downloaded
archive rather than assuming an Actions PASS meant usable headers.

Fixed `.github/workflows/native-v214-win64-cross-sdk.yml` to copy
headers with `cp -aL`, and reject symlinks/missing C headers.
The successful new portable archive contained **1,633 regular files,
zero symlinks**, about 69.5 MB unpacked; archive SHA-256 verified.
The separately generated V195 QPC timer patch was applied to the local
pinned upstream `rc.h` and independently matched the SDK
`patched_rc_sha256` fingerprint.

**Real private native Win64 COFF generated from the owner's original game C:**

| Module | COFF size | Result |
| --- | ---: | --- |
| Full 241,031-function `recomp.c` registration table | 34,841,097 bytes | Windows x86-64 COFF |
| `recomp_00000.c` original translated game functions | 4,450,135 bytes | Windows x86-64 COFF |
| One among the largest generated gameplay C shards | 11,358,860 bytes | Windows x86-64 COFF |

This is real original-game code cross-compiled with:
`clang --target=x86_64-w64-windows-gnu -std=gnu11 -O0
-ffp-contract=off -fno-strict-aliasing`, genuine pinned
upstream C headers and a public MinGW SDK. No private generated
game C or native objects are uploaded to GitHub.

## New resumable private build helper

`compile_private_win64_coff_v217.py` checks SHA-256 of source shards,
upstream Git HEAD, the exact V195 patched runtime header, V214 SDK manifest,
clang target/optimization settings and every cached object. It writes
bounded private compile logs through V210 and atomically saves a
per-object manifest. An exact second run on the registration table
and first module reported **2 verified objects reused, 0 rebuilt**.
The largest example module then compiled separately. This permits
safe, gradual conversion of all 384 C modules without rebuilding
completed objects after a chat/session interruption.

Example (PRIVATE machine, private paths outside all Git worktrees):

```bash
python native/source-port/recomp-v194/compile_private_win64_coff_v217.py \
  --generated-dir /PRIVATE/generated_full \
  --upstream /PRIVATE/pinned-bloodborne-recomp-v195 \
  --sdk /PRIVATE/public-win64-sdk \
  --output-dir /PRIVATE/win64-v217 \
  --file recomp.c --file recomp_00000.c
```

The Linux/Windows public V217 CI uses **invented C only** for
COFF validation, includes a real public MinGW SDK compiler check on
Ubuntu and verifies that a second call reuses the original synthetic
object rather than rebuilding.

## Technical boundaries

1. Passing C compilation does NOT mean 241,031 functions have a
   proper native ABI, executable Win64 linkage, valid relocations,
   or all CPU flags/native dependency semantics.
2. The registered function table contains references to the entire
   function set. Linking only the three compiled COFF objects
   is not a runnable game.
3. The current generator still emits 1.468 million static calls to
   guest runtime callbacks. Replacing or eliminating those paths,
   plus proper game import/runtime/graphics/audio/resource/system
   subsystems, remains necessary for a true EBOOT-free PC game.
4. No Fornex changes, PR merges, game uploads or original source
   redistribution occurred. Game boot is **NOT proven**.

## Latest verified continuation: multi-shard original Win64 build

After the initial three actual original-game objects, the private
V217 builder successfully compiled **eight additional original
generated C shards**, sampled from different parts of the full source
set. **Eleven distinct actual x86-64 Windows COFF objects** now exist,
each represented in the private SHA-256 cache manifest. First two
original objects were independently rerun and **reused without
recompilation**. These are code-generation/COFF facts, not executable
gameplay or OS service integration.

The clean public integration job initially failed because an
upstream Git checkout lacked generated Zydis headers. Aligned
the workflow with V214's pinned `V196 -> V195 -> CC=clang ./build.sh`
sequence. The revised synthetic-only CI passed **both platform
selftests and actual portable MinGW cross-C compilation + reuse**:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41318386647

The V216 independent original-game callback count remains
**1,468,066** static callbacks; compiling objects does not remove
them. No EBOOT-free playable build is claimed.
