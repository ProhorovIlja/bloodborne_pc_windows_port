# V207: distinguish original-game functions found from functions registered as native AOT

## Why this gate is needed

Original \`tools/recomp/scan.c\` emits a function index, but upstream
\`tools/recomp/bbrecomp.c\` deliberately excludes import stubs and some
functions calling setjmp from its \`RcFunction table[]\`. Therefore a
successful full-image scanner pass or an apparently successful generator
invocation does **not** mean that every discovered game function was
compiled. Numbers in a scan manifest must not be labelled as the count
of natively translated functions.

## Change

\`verify_generated_coverage_v207.py\` reads only the **private** genuine
generator's \`recomp.c\` table and verifies:

- Exact original full-function \`RcFunction\` row shape; reject unexpected
  upstream table-format changes, malformed entries and missing tables.
- Function/dispatch identifiers match, sizes are positive, original code
  offsets are strictly increasing (no missing-sort or duplicate rows).
- Table registration count is nonzero and no greater than the scanner count.
- Separate outputs \`functions_scanned\`, \`aot_functions_registered\`,
  \`functions_not_in_aot_table\`, and whether all scanner rows were registered.

V204 private Linux preparation records these in the manifest.
V204 Windows compiler **independently rereads** the generated table and
rejects stale or misleading manifest coverage metadata before compilation,
in addition to its existing SHA-256 generated C checks and V202 fallback
runtime strict gate.

The **difference** is the count of scanner rows not registered in the
AOT table, NOT necessarily a count of unique untranslatable instructions.
A table entry may still contain guest-runtime fallbacks; those continue
to be separately audited. \`complete_scanner_to_aot_registration=true\`
does not prove an EBOOT-free engine or game boot.

## Validation and privacy

\`.github/workflows/native-v207-full-aot-coverage.yml\` performs Python
syntax/import and synthetic table adversarial tests on Windows and Linux.
Only invented table rows run in public Actions. Real original code,
metadata pointers, offsets, game assets and original C/COFF remain private.

The real 1.09 encrypted/wrapped and decrypted inputs already exist in the
owner's Drive \`CUSA03173\`; use **\`eboot.bin-decrypted\`** for offline
analysis. The full original-game scanner/generator/COFF pass has **not yet
been independently executed**. V207 ensures the first private batch
reports its actual native registration coverage rather than inflating
a progress metric.

Draft PR #84 only. No PR merges, production updates, or Fornex changes.
