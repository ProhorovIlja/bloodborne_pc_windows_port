# V478: connect relocated data to checked 1074 call routes

V474 now feeds V464 and V465 through a shared bounded adapter in an
integration test. The two vtable getters and both structure-return sites
check their target IDs against relocated memory, without a guest executor.
The return write can only touch a dedicated scratch span; executable code
is neither mapped nor needed by the host binary. An invalid route leaves
the tested output and data unchanged.

The owner-local CUSA03173 1.09 test verifies the four callsite encodings,
the three executable-relative relocation cells and the three leaf bodies
offline. The four static Linux candidates (GCC/Clang x two guest slides)
then ran in a chroot with only host binaries: 16 accepted route calls and
24 negative cases for target tampering and invalid result addresses. The
public synthetic fixture also checks read bounds, disjoint regions and
scratch canaries, and ran under Clang ASan/UBSan. The receiver objects and
their fields are synthetic in these tests; only route provenance and
vtable relocation targets come from the original image. No original bytes
or generated retail plans are committed.

This is not the complete 1074 control flow. Registry and allocator paths,
mutex integration and the warm singleton receiver must still be checked
against state left by 1–1073. ShadPS4 initializes per-thread TLS before
entering guest thread code; PS4Recomp supports multi-module TLS. Neither
makes this single-controller adapter a substitute for full TLS or threads.
