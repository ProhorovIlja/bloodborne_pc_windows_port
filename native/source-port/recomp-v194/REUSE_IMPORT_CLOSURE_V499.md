# V499: reuse candidates for native-only startup

Do not compare repository headline import/function totals as if they shared an image or denominator.
The same NID can have multiple library/module selectors and symbol types. Selectors in this
inventory belong to the exact input image, not the upstream's ELF or a different CUSA.
V499 compares relocation-backed keys and slots with explicitly declared candidate bindings.
The private profile uses format bb-host-import-inventory-v1, image_sha256, and bindings rows
[NID, library selector, module selector, ELF symbol type]. Exit 3 means unmatched keys,
2 means malformed/mismatched input; 0 means metadata matches, not a runnable ABI.

- bloodborne-native/bloodborne-recomp: first reuse candidate for C generation and differential
  testing; existing V204 integration is the starting point. Generated functions depend on
  guest state and fallback paths; importing its library alone does not replace startup.
- bloodborne-native/bloodborne-runtime: already integrates that generator; use as the first
  baseline for measuring fallback and loading dependencies. Its docs/layers/executable.md
  still describes startup from a prepared PS4 executable.
- droogie/bbhost and visy/bloodborne_pc_windows_port: candidates for x64 host services and
  graphics fixes, not drop-in providers for the recomp ABI. Validate layout/calling conventions
  and licensing before adopting code.
- boykopovar/AnyPS5 #3093/#3094: PS4 homebrew proof and relevant SCE/RELRO/jump-table
  diagnostics, not a Bloodborne boot. Retail test was CUSA00900; do not import its offsets.
- wie-project/PS4Recomp: alternate Apple Silicon AOT and Metal reference, not evidence for
  this image or for Windows/Linux native-only startup.

Next runtime check: offline generate against the pinned original, use a prepared-only launch
root, disable guest execution fallback, and record first missing route with OS-level file
and module tracing. Keep retail files, generated game code, and private inventory out of Git.
