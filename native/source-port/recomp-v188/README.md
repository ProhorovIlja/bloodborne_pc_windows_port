# V188: Windows LLVM COFF backend for original bbrecomp-style generated C

This is an **incomplete source-port compiler pipeline** and specifically is **not a Bloodborne Windows release**. It compiles a bounded local set of `recomp.c`, `recomp_1.c`, ... C units to genuine Windows x64 COFF object files using Clang and links an actual PE32+ DLL via `lld-link`.

The pinned public upstream `bloodborne-native/bloodborne-recomp@8f31ec7c41f252730c6325d52647046baef7549f` emits `bb_recomp_init` with a Unix visibility attribute. `lld-link /EXPORT:bb_recomp_init` explicitly exports this name under Windows even when no `__declspec(dllexport)` exists. The script rejects non-AMD64 object output, malformed PE DLL or absent exported initialization function before publishing the output.

### Verified synthetic example

```powershell
python native/source-port/recomp-v188/win64_coff_link_v188.py `
  --source-dir native/source-port/recomp-v188/fixtures `
  --out build-v187/Release/v188_generated.dll `
  --include-dir native/source-port/recomp-v187
.\build-v187\Release\v187_host_probe.exe `
  .\build-v187\Release\v188_generated.dll `
  .\build-v187\Release\v187_bad.dll
```

The sources are **only synthetic**. The fixture deliberately splits one generated-style table and one generated-style game function across two separate files, so the linker resolves actual cross-object symbols. It omits the Windows-specific export attribute to reproduce the upstream interface bug. The real Windows host loads the DLL and calls its function through the pinned public ABI v4, then rejects a deliberately invalid module.

### Real user's game: not ready and not put in CI

This tool accepts **private C units only if the user generated them locally** from their own Bloodborne game. No code or generated C, object, DLL, confidential file path, game image or private trace may be uploaded to GitHub. The current upstream generator and library builder still target macOS ARM64 and depend on `bbcpu`, PS4-shaped memory/TLS, runtime callbacks, libraries and exception semantics. A full generated library will probably **not link** under the current strictly freestanding `/NODEFAULTLIB` link policy; this V188 compiler must not silently pull in unknown CRTs or claim compatibility. The *next* step is source-exact Windows x64 generator integration with the actual `src/recomp/rc.h` and `BbCpu` layouts, controlled C-runtime symbol resolution and differential instruction/call tests on a private machine. Only after that could independent Windows APIs and native renderer remove runtime PS4 dependencies.

`win64_coff_link_v188.py` never invokes a shell, prints only counts/booleans, uses temp objects, emits the final DLL atomically and refuses symlinks, truncated units and unknown source patterns. The script is for code built locally from an authorized game copy, not publication of copyrighted derivatives.
