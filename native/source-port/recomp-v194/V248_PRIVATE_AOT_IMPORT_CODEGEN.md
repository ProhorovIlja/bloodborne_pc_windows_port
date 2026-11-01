# V248: real private game import index -> Windows-native AOT C

Date: 2026-11-01. True no-EBOOT native Windows port, PR #84.

Earlier V245 bootstrap installs an actual `RcApi.call` chain for
math and TSC clock primitives before calling generated
`bb_recomp_init`. However its CI fixtures had **synthetic** imported
offsets. V248 now adds a build-time-only bridge from the privately
extracted original Bloodborne `scan/imports.tsv`, schema
`stub\tname`, to a generated native C translation unit.

`build_private_aot_imports_v248.py`:
- Reads a bounded owner-owned TSV; rejects symlinks, duplicates,
  malformed rows, missing names and oversized files.
- Requires exactly the already verified 23 math shim names plus two
  BBHost-backed clock **name candidates**:
  `sceKernelReadTsc` and `sceKernelGetTscFrequency`.
  Their presence in BBHost is not proof they're both in the owner's
  original 1.09 imports; missing any required symbol means **hard
  failure**, not an invented offset or a replacement guess.
- Writes a PRIVATE source file with `0600` create-only permissions,
  refusing existing targets, symlink output, symlinked ancestors and
  any path under a Git worktree. A failed run cannot overwrite it.
- Emits `shyt_private_aot_imports_v248_init(image_base, math, clock)`,
  which builds the real `ShytMathImportTable` and
  `ShytClockTargetsV239` with runtime image base, allowing the
  existing V245 initialization to receive a single original import
  configuration. The generated C is compiled/linked with game AOT
  code ONCE, and does not open EBOOT/ELF at runtime.
- Never prints individual imported addresses, game byte data, or
  source text; only one aggregate completion marker on success.
  No private games are read by GitHub Actions.

Example on the OWNER'S PRIVATE build machine (not public CI):

```sh
python native/source-port/recomp-v194/build_private_aot_imports_v248.py \
  --original-imports /private/bb/scan/imports.tsv \
  --private-output /private/bb/build/original-imports-v248.c
```

Then include the private generated C in the owner-only Win64
AOT build and call its initializer with the actual pinned image base
BEFORE `shyt_aot_services_bootstrap_v245`. This bridge is not
automatically wired to a complete 384-module private build: that
full native executable still requires proprietary source ownership,
correct AOT object linking and Windows subsystem replacements.

`test_build_private_aot_imports_v248.py` uses synthetic import
indices to check correct C generation, refusal of malformed TSV,
duplicate offsets/names, missing clock imports, public worktree
paths, symlinks, oversized content and accidental overwrite.
`native-v248-private-aot-import-registration.yml` runs the fixture
on Windows and Ubuntu.

No live game boot, original game binary, Fornex deployment, or
verified latest GitHub Actions completion is claimed.
