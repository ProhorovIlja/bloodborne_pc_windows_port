# V208: FIRST REAL PRIVATE ORIGINAL BLOODBORNE ELF/FDE READ (2026-11-01)

This is **actual analysis of the owner's decrypted Bloodborne PS4 executable**,
not a generated fixture. Source provided privately from Drive CUSA03173.
The executable binary, extracted function list and raw code stay PRIVATE.

## Reproducible offline read

`audit_private_original_fde_v208.py` uses only Python standard-library
`mmap` and `struct`. It validates ELF64 x86-64 PS4 type 0xFE10, original
PT_LOAD program headers and the PT_GNU_EH_FRAME table, then checks every
FDE's PC-relative function start, positive range, bounded executable
segment, actual CIE record and no overlapping/sorted function extents.

Run against a LOCAL PRIVATE file, never through public GitHub Actions:

```
python native/source-port/recomp-v194/audit_private_original_fde_v208.py \
  --input /private/CUSA03173/eboot.bin-decrypted \
  --output /private/bloodborne-fde-audit.json
```

Private tested original input: 93,667,640 bytes; ELF type 0xFE10;
10 program headers, zero ELF section headers; executable PT_LOAD on-disk
84,776,668 bytes. The .eh_frame_hdr reported and independently validated:

| Private original metric | Actual result |
| --- | ---: |
| FDE records | 162,959 |
| Unique function starting addresses | 162,959 |
| Records with matching pcrel start and bounded span | 162,959 |
| Records with valid CIE back-reference | 162,959 |
| Distinct referenced CIEs | 4,363 |
| Total non-overlapping function range bytes | 41,719,719 |
| Incorrect records under checked rules | 0 |
| Overlapping reported function ranges | 0 |

A separate PRIVATE `FDE function range index` of all 162,959
start/length pairs was derived for comparison with the full scanner.
It is **NOT** upstream `scan/functions.tsv`: there are NO decoded
instruction counts or undecodable-instruction classification in it.
No function address or original instruction is published here.

## IMPORTANT what this does not mean

- FDE entries represent unwind-described ranges. They are **not** proof
  of all functions, executable coverage or translation.
- 162,959 is NOT the number of native Windows functions compiled.
- Neither the game version 1.09, relocation correctness, PS4 imports,
  unwind execution, Vulkan/audio/runtime services nor game boot can
  be inferred solely from an ELF header and FDE table.
- The existing 9,955 strict leaf-function candidate cohort and earlier
  V207 AOT registration tests are distinct. Do not sum/inflate those
  metrics or declare the native PC game finished.
- Full pinned bbrecomp instruction scan -> C generation -> Win64 COFF
  compilation -> import/runtime closure -> native game startup remains
  to be performed and measured privately.

Public Windows/Linux self-tests use invented tiny ELF/CIE/FDE only.
No retail input or extracted code is ever committed or uploaded to CI.

## Next blocking stage

Use the existing V204 private full original pipeline with the original
game file (available privately) and a pinned local copy of the
upstream `bloodborne-native/bloodborne-recomp` tools. The current
runtime could directly audit the genuine ELF but did NOT have a
working checkout of the upstream code generator, so it could not run
the real instruction decoder/AOT compiler this turn. Refuse claims of
full compilation until actual private tool outputs and native Windows
runtime evidence exist.
