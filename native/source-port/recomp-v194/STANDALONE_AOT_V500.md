# V500 — standalone AOT comparison

wie-project/PS4Recomp at 8ae98bc68e414ea879746998b570afd119ad57bf is an actual Apple Silicon comparison target: upstream reports CUSA03173 in-game. Its standalone packager filters eboot.bin, .elf and .prx recursively (pkg/cli/cli.go); that does not rule out external reads or embedded guest code. The /app0/eboot.bin string in recomp_runtime.c's argv setup is not itself a file open. The code has a guest setjmp/longjmp path but the assembly backend aborts on guest C++ exception handling.

bloodborne-native's tools/recomp/modules.py already adds both libc.prx and libSceFios2.prx to the generator's view, so do not write a fresh lifter for them first. Reuse the multi-module path; verify the remaining import stubs and nonlocal transfers independently of ordinary call coverage. Do not transplant PS4Recomp's arm64 trampoline into Windows x64.

Run audit_bundle_v500.py on a disposable prepared launch tree before a trace-based boot. It detects some loose originals (including renamed SCE ELF/SELF) and flags links; it is not a sandbox, does not unpack archives or inspect embedded data, and cannot attest runtime closure. Use a stable, isolated tree and OS file/module tracing to prove the process cannot access the dump. Compare menu, first controllable frame, level transition and save reload with the original unavailable. No game artifacts in Git.
