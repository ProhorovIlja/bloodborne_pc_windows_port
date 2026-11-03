# V216 actual full-original-image AOT/runtime audit, 2026-11-01

## Source: PRIVATE decrypted real Bloodborne PS4 executable

The owner-provided 93,667,640-byte `CUSA03173/eboot.bin-decrypted`
was run through the locally unpacked, public-pinned V213 upstream
`scan` and patched `bbrecomp` binaries. NO original source code,
function offsets, image, or generated C are committed to GitHub.

**Actual completed private stages:**
- Original full function scanner: **241,821** records, sorted valid
  `scan/functions.tsv` format.
- Original patched generator: **384** `recomp*.c` modules,
  **1,585,909,087** source bytes, success status in local private log.
- `verify_generated_coverage_v207.inspect_file` exact address/size
  parity: **241,031** registered `RcFunction` entries, **790**
  scanner records not in generated AOT table. Full registration FALSE.
- `clang -std=gnu11 -fsyntax-only` passed **14 actual original
  source shards**, including a large shard, with zero syntax errors.
- Host Linux x86-64 `clang -O1 -c` compiled one real 4-MB generated
  source shard to a 1,250,864-byte ELF object. This is NOT Windows COFF
  and retains original guest callbacks.

## The remaining strict native-runtime blocker

A full lexical audit of every generated C file, **ten resource-bounded
private batches**, detected exactly:

| Original generated callback | Occurrences |
| --- | ---: |
| `rc->call` | 630,445 |
| `rc->tail` | 367,418 |
| `rc->bail` | 367,418 |
| `rc->step` | 102,785 |
| `rc->trace` | 0 |
| **Total** | **1,468,066** |

Callbacks appear in **383/384** C modules. The strict V202 gate
**does not pass**. These counts are **static call-site occurrences** in
generated source, not distinct functions executed at runtime, not runtime
frequency, and not an estimate of completion percentage.

This source set cannot legitimately be called a complete
EBOOT-independent engine. Native Windows compilation (COFF), replacement
of legacy `RcApi` fallback behavior, relocations, OS imports, audio,
graphics, game initialization, assets and first gameplay boot are
separate unsolved stages.

## Resource-stable reproducibility

Added `audit_native_runtime_stream_v216.py`, a **bounded-memory**
lexical C scanner that excludes comments, strings and char literals.
It prints only a compact aggregate. In private tests, the 55-MB
8,192-function batch completed in **4.59 seconds** with ~**97 MB peak
resident memory**; entire 1.59-GB original code set was audited in ten
batches of ~159 MB each. Exact lexical counts matched independent V202
on 12 representative original shards, including largest/smallest; all
five aggregate callback totals match a separate fast raw source scan.

The full legacy V202 audit **did not produce a completion report** in
this execution environment; don't label it PASS. V216 provides verified
bounded-memory coverage, while retaining V202 as the comparison
reference on controlled smaller inputs.

Public V216 synthetic Windows/Linux source-only CI:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41317453075

No game bytes or user logs on GitHub. No PR merged or Fornex changes.
