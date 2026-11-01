# V218: recover real Bloodborne Win64 COFF work safely after stream interruption (2026-11-01)

Context: the owner reports recurring ChatGPT UI **Error in input stream**.
A specific platform root cause is NOT established and cannot be patched via
GitHub. Official troubleshooting: https://help.openai.com/en/articles/7996703-troubleshooting-chatgpt-error-messages .
The OpenAI status history listed no new incident for November 1 when checked.
A direct attempt at *streaming* container execution also failed with
`StreamingExecNotEnabledContainerError` before the build started. This is
a separate observable tool-layer limitation, not proof of the UI error's cause.
Use ordinary non-streaming, short, bounded calls instead.

## ACTUAL original-game private AOT COFF progress

- Input remains the owner's original decrypted Bloodborne 1.09 ELF.
- V213 whole-game source still has 384 generated C files, 241,031
  registered original-function table rows; 1,468,066 **static** guest
  callback occurrences remain (see V216). This is NOT yet an
  EBOOT-independent playable PC engine.
- At start of this continuation, **11** original Win64 COFF objects were
  present with a SHA-256 checkpoint.
- First bounded real-original V217 batch: 3 new objects.
- Second bounded batch: 8 new objects.
- Third overly large 14-file batch exceeded tool execution time; **9**
  completed objects retained their atomic manifest entries. One untrusted
  partial COFF object was moved to a PRIVATE quarantine, not counted as
  complete, and no compiler process remained.
- A new short V218 smoke batch compiled 3 additional real original modules
  successfully using the 45-second budget.
- **Final independently verified: 34 Win64 AMD64 COFF objects**, zero
  SHA-256/COFF machine/section/size mismatches, **168.46 MiB** total.
  These were only selected real source shards + table, not all 384.
- Actual private checkpoint remains in
  `private_coff_manifest_v217.json`; original code/objects/hashes are
  never copied into public GitHub or the chat transcript.

## Code change

Modified `compile_private_win64_coff_v217.py` to enforce at most
**four source files per invocation**, and a new
`--budget-seconds` argument (default 45, accepted 10-3600). It
checks the deadline before starting each object, uses the remaining
budget as the private compiler-stage timeout, retains the atomic
per-object SHA-256 manifest, and reports `deferred_files` if the
remaining inputs cannot be reached within the budget.

Why: an earlier oversized synchronous compilation was stopped by tool
timeout. Persisting successful objects means the task is still
resumable, but a failed compiler may leave an untrusted partial on an
abrupt external stop. Keep the existing fail-closed partial-object
handling; do not silently reuse incomplete objects. Verify no process
is writing before quarantining any partial.

Public source-only GitHub CI after the change:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41319362081
**SUCCESS**. Related native V194 CPU/ABI validation:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41319362133
**SUCCESS**.

## Limits and next gates

The remaining 350 original C source shards still require compilation,
then verified linking. Individual COFF objects retain guest runtime
calls, and have not been linked into an original-game Windows EXE.
Strict no-guest-runtime, Windows services, native renderer/audio,
asset handling, PS4 import replacement, and first real game boot
are NOT proven. Keep PR #84 Draft and do not touch Fornex.
