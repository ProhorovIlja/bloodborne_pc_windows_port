# Strict startup RcApi replay

After the V434 rebuild gate, prepare the V435 native routes from independently verified continuation and target pairs. Preserve the constructor ordinal as host-owned state. Run the audited driver for each constructor through V436; keep one VM and CPU across the ordered replay. The fixture exercises the real RcApi.call signature, not a direct invocation of the V435 lookup.

Use the callback directly only for a native-CALL-only driver. If the retail harness already routes imports, preserve those exact import handlers and send only its native branch to V436. Do not use a caught error to try another implementation. Do not change the main launcher or the normal game runtime to use this startup-only adapter.

A denied or malformed native return immediately leaves the C replay through the existing cooperative checkpoint. This releases the VM pin but does not roll back earlier guest writes. Stop on anything other than COMPLETED and discard the replay state; do not continue from a recovered CPU. The driver still owns the outer return checks, and V424 still checks the private transcript against retail order. No general signal/exception recovery or retail execution result is claimed.
