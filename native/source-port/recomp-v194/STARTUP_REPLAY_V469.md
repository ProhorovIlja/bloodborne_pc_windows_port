# V469: linked native replay of one verified startup family

V468 replayed 390 selected registration leaves from ordinals 1074–1500.
V469 scanned all 18,444 legacy callbacks in the owner-local CUSA03173 1.09
image, found 12,045 exact 41-byte leaves of the same form and checked their
writable 16-byte object/guard spans and executable-relative table slots.
There are 1,020 such leaves in 1–1073, 390 in 1074–1500 and 10,635 later.
Three object/guard pairs account for all 12,045 (4,015 each).

The offline private generator collapses equal objects, emits a sorted
object table and uses bounded object indices in the ordered sparse plan.
The C runner validates every object and step before the first native call.
No runtime pack, Python, ELF loader, original guest code or console library
is needed. Do not ship the private header, executable or raw trace. The
public default header is synthetic. Its CLI traces are diagnostic output
only; the built-in checks are not a provenance certificate.

Linux x86-64: reference ran only opcode-verified leaves from RX pages;
candidate binaries (GCC and Clang, static) ran with only those two native
binaries in a chroot and no ELF guest image, assets or shared libraries.
For each compiler, all 12,045 normalized per-step trace lines matched.
Both tested immediate reentry, yielding 48,180 candidate invocations total.
Three initializations and 12,042 already-set guards per run. The reference
checked neighboring object states and outside canaries; candidate state
has separate canaries. Clang ASan/UBSan passed the public fixture and
rejected duplicate ordinals and an invalid object index before output.

This is an isolated sparse projection of startup, not real constructor
order with all side effects: 6,399 other callbacks are omitted. In
particular, don't infer that those callbacks leave the three objects
alone or that this crosses 1074. The verified contiguous prefix is
unchanged. N64Recomp provides an independent model for mapping guest IDs
to compiled code. ReXGlue itself loads original XEX code read-only for
data compatibility despite using a prebuilt dispatch table, so it isn't
a model for excluding original code bytes from runtime altogether.
