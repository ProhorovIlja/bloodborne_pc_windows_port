# V219: source/header/compiler-accurate cache for private original Win64 COFF

Date: 2026-11-01. True project goal remains a complete native Windows
Bloodborne executable without original PS4 EBOOT required at runtime.
Source-derived original-game bytes/objects stay **private**.

## Observed and corrected cache weakness

V217's resumable object cache originally keyed only the original generated
C file SHA-256, patched `rc.h`, SDK manifest checksum, compilation
settings and the compiler version *string*. **A changed nested Zydis,
upstream C header, MinGW SDK header or compiler executable could silently
reuse an incompatible cached COFF**.

New V219 helper `verify_coff_dependencies_v219.py` creates SHA-256
input fingerprints of the contents and relative filenames of **all**
files in upstream `deps/include` and portable `sdk/include`, relevant
headers in upstream `src`, plus the actual resolved clang binary.
Bounds: max 20,000 included files, 512 MiB combined headers, 64 MiB
per header, 256 MiB compiler. Rejects unsafe symlinks and unexpected
file types. This fingerprint is included in every new V217 compile
recipe and cached object's comparison.

**Existing V217 records without V219 fingerprints remain present on
disk but are NOT reused under the stronger rule.** Such objects must be
recompiled/revalidated when selected. This is deliberate fail-closed
cache migration, not data loss.

## Verified on actual original-game source

At continuation start: **34** real Win64 AMD64 COFF objects, each SHA
verified. Before cache change: 4 more original C modules compiled.
After change: 4 additional distinct original game modules built, a
second identical invocation **reused 4/4** without recompiling, then
4 more original source modules compiled.

**Total in private manifest now: 46 / 384 COFF modules, no observed
SHA-256, size or AMD64 machine-format mismatches.** Eight COFF objects
have the new dependency key; 38 are historical verified byte blobs
that lack a V219 dependency-proof key. This count is NOT a game
completion percentage: these COFF files can still refer to a large
guest CPU runtime. True Windows link, renderer/audio, ABI closure and
native no-EBOOT game boot have NOT been achieved.

## Tests

Local synthetic with actual pinned public headers and compiler:
- first compile: **1 new**
- same files/headers: **1 reused**
- add an otherwise unused SDK header: **1 rebuilt**
- hash mutation unit tests cover upstream header, SDK header,
  compiler executable, and rejected symlink.
- No original binary, C source, addresses or native object is sent to CI.

The cross-platform public workflow
`.github/workflows/native-v217-private-cross-coff.yml` includes
Windows/Linux parser tests and Linux compiler+cache invalidation.
The first upstream CI run of the new integration test failed while the
same test passed locally. A bounded public-only failure phase/artifact
was added to triage that runner difference **without fetching full
GitHub Actions logs**. Do not mark this new integration test as PASS
until its latest run succeeds.

## Follow-up

Recover the bounded error category and fix the CI cause. Continue
original-game COFF conversion in batches of 1-4 files and bounded
execution time. Prioritize reduction/removal of the separately measured
1,468,066 static guest callback sites before representing the generated
function table as a complete native engine. Keep PR #84 Draft and
Fornex unchanged.
