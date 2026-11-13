# Native startup: V409

The original retail entry calls environment setup, registers loader and image
cleanup, calls an initializer dispatcher, then enters main with argc, argv and
a zero third argument. The wrapper forwards main's return status to the
return-notification and exit imports. This is static ABI evidence, not a
retail execution trace.

The host lifecycle in this branch takes explicit adapters for those operations.
It owns its exit stack and does not exit the host process. The initializer
plan validates every ID against a host binding registry before invoking a
constructor. Forward tables run in storage order; legacy tables run in reverse.
Constructor bodies and their indirect callees must still be independently
verified and bound. A missing binding rejects the plan; it is not skipped.

Next integration gate: privately generate the ordered initializer plan and
compare it to the owner-built AOT registry. Report missing/unsupported
initializer bindings before attempting main. Implement process-environment
and TLS adapters against independently verified semantics. The lifecycle
test uses invented callbacks; it does not execute retail code.

References: bloodborne-native/bloodborne-recomp (pinned 8f31ec7) import names,
bloodborne-native/bloodborne-runtime (2340067), and deadinside28/bloodborne_pc
(0fc2921). The runtime/loader paths are useful references but do not meet
the requirement of an independent executable without runtime PS4 EBOOT.
No upstream source was copied into this change.
