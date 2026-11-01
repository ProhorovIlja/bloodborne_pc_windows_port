# V212: preflight the real private original executable and pinned patched recompiler

2026-11-01 continuation, PR #84. The owner's original private
`CUSA03173/eboot.bin-decrypted` is already present and has NOT been
uploaded to GitHub. The 93,667,640-byte file was examined **locally**
in the model's working container; its x86-64 PS4 ELF type, header,
executable/unwind segments and declared 162,959 FDE rows passed the
new V212 preflight. V208 previously checked each FDE separately.
The working environment reports about 30 GiB free space.

**Actual limitation:** outbound container DNS/network could not resolve
github.com, and the upstream source checkout is not locally present.
GitHub's *connector* can inspect text and update our repository, but
that does not supply a runnable full build tree into the container.
Therefore `ready_to_start_private_full_scan=false`; a full original
`scan -> bbrecomp -> generated C -> Win64 COFF` has NOT run.

## New file and real pipeline integration

`native/source-port/recomp-v194/private_original_preflight_v212.py`

- Fail closed unless input is decrypted PS4 ELF64 x86-64, type FE10,
  valid program table, executable segment and EH-frame header/count.
  Declared FDE count is **not** a full range validation.
- Verify original upstream Git HEAD equals
  `8f31ec7c41f252730c6325d52647046baef7549f` and that
  V199/V200/V201/V203 generator patches are present.
- Check original `bbrecomp`/`scan` executables exist, are executable,
  and are not older than the current generator/scanner source.
  **Limitation:** timestamps alone cannot cryptographically prove a
  compiler built the binary from those files.
- Reject accidentally writing full game outputs into a Git repository,
  and require at least 16 GiB free by default before private work.
- Only emit a short JSON summary of readiness/declared function count.
  Do not echo game paths, original bytes, function addresses or logs.

V204 now invokes this gate **after** its existing original-file presence
check, preserving the earlier CI contract when no private game is
available. V210 bounded subprocess output and V211 metadata-only stage
status remain in effect.

## Local private invocation

```bash
python native/source-port/recomp-v194/private_original_preflight_v212.py \
  --eboot /PRIVATE/CUSA03173/eboot.bin-decrypted \
  --upstream /PRIVATE/bloodborne-recomp-pinned-and-patched \
  --work /PRIVATE/bloodborne-original-v204
```

When this passes, run V204 preparation using the same pinned,
already-rebuilt tools. The original input is an offline **build-time**
dependency; the final native game must not need EBOOT at launch.

## Validation

Actual decrypted private original: header and FDE-count check passed;
no upstream toolchain readiness claimed. Public Ubuntu/Windows
synthetic input tests and intentionally missing upstream checkout
rejection: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41313180548 .
Source-only V203 original generator and Windows COFF tests are separate,
not a substitute for the private full-game run.

No Fornex deployment, public game upload or merge performed.
