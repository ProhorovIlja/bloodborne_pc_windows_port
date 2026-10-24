# Licenses and third-party notices

This document describes **what the project actually uses**, where upstream
copyright/license notices are found, and which redistribution checks remain
open. It is informational, **not a claim that every external repository is
freely reusable**. Individual authors retain copyright in their work.

## License scope and important difference between repository branches

The **mainline's native game, BLauncher, co-op and shadNet sources are fetched
from Yharnam Together** at commit
[`77e350743a7cb4524cfcc1782fb6e3af64e25b15`](https://github.com/lKaniel/bloodborne-server/commit/77e350743a7cb4524cfcc1782fb6e3af64e25b15).
That upstream explicitly states **GNU GPL version 2 or later**, with license
documents at [`LICENSE`](https://github.com/lKaniel/bloodborne-server/blob/77e350743a7cb4524cfcc1782fb6e3af64e25b15/LICENSE),
[`bbport/LICENSE`](https://github.com/lKaniel/bloodborne-server/blob/77e350743a7cb4524cfcc1782fb6e3af64e25b15/bbport/LICENSE),
[`server/LICENSES/`](https://github.com/lKaniel/bloodborne-server/tree/77e350743a7cb4524cfcc1782fb6e3af64e25b15/server/LICENSES) and
other component-specific directories. The upstream uses separate copyright
and third-party license notices.

The top-level [`LICENSE`](LICENSE) of **this historical repository**
contains **GPL version 3** text. It was present before the Yharnam Together
mainline was established. **It does not unilaterally relicense Yharnam
Together or any included third party.** Rights in each original file remain
governed by its copyright notice and applicable license. Compatibility of
the final combined work, including any GPL-2-only or proprietary-component
restrictions, must be audited before redistribution. No unqualified
whole-product license claim is being made while this audit is incomplete.

A GPL-2.0-**only** component cannot simply be combined with GPLv3-covered
code, but a component available under GPL-2.0-**or-later** may permit
GPLv3 combinations, depending on every linked or bundled dependency.
**Maintainer approval of an external project is not inferred from a license.**

See [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
and the [FSF GNU GPL compatibility FAQ](https://www.gnu.org/licenses/gpl-faq.en.html).

## Licenses and notices already included by upstream packaging

The pinned upstream's
[`bbport/packaging/windows/package.sh`](https://github.com/lKaniel/bloodborne-server/blob/77e350743a7cb4524cfcc1782fb6e3af64e25b15/bbport/packaging/windows/package.sh)
copies its original `LICENSE` and **individual runtime licenses** into
the portable ZIP's `licenses/` folder, including where actually bundled:

| Component or origin | Attribution / notice location | Status |
| --- | --- | --- |
| Yharnam Together native game | `bbport/LICENSE`, upstream `README.md` | Current pinned base, GPL-2.0-or-later per upstream |
| shadPS4 renderer and network ancestry | `emulator/LICENSES/`, shadPS4 upstream | Included by Yharnam Together; check individual files |
| shadNet native backend | `server/LICENSES/GPL-2.0-or-later.txt` and other server notices | Included and built separately on Windows and Ubuntu |
| FireBurn FSR-Vulkan, AMD FidelityFX SDK | `licenses/FireBurn-FSR-Vulkan-LICENSE.txt`, `licenses/AMD-FidelityFX-SDK-LICENSE.txt` | License files copied by upstream's Windows packager |
| NVIDIA DLSS SDK/runtime and bridge | `licenses/NVIDIA-DLSS-LICENSE.txt` and `licenses/bbport_dlss-LICENSE.txt` | Conditional on runtime actually being included; verify NVIDIA terms |
| Intel XeSS | `licenses/Intel-XeSS-LICENSE.txt`, `licenses/Intel-XeSS-third-party-programs.txt` | SDK license and third-party notices copied |
| ReShade and preset shaders | `licenses/` entries copied from upstream ReShade package | Each third-party license kept |
| PkgTool / LibOrbisPkg | `licenses/PkgTool-LICENSE.txt` | Redistribution of its binaries requires that notice |
| Qt 6 (Windows shadNet and Ubuntu server) | Qt's distributed notices, applicable Qt LGPL license and source obligations | **Windows server Qt DLL license deployment requires further review** |
| MSYS2 / LLVM / SDL3 / FFmpeg and other native runtimes | `licenses/` and individual runtime documentation | Actual ZIP contents must be matched to notices, not guessed |
| GLSL, Vulkan, third-party git submodules | Upstream `.gitmodules` and each component's own LICENSE | No blanket claim that all submodules are MIT |

This is a **summary, not an exhaustive software bill of materials**. The
upstream ZIP's actual DLLs and libraries and the resulting package's
`licenses/` directory are the authoritative items that must be checked.

## Mandatory distribution checklist

1. **Pin source commits**, record the repository URL, original author, exact
   file path, license and all modifications in [CREDITS.md](CREDITS.md).
2. Keep **copyright headers, licenses and notices intact**, alongside source
   code. Do not delete original commit history/attribution from documentation.
3. Verify every **redistributed DLL and embedded library** has the full
   applicable license, notice and source availability when required,
   including Qt LGPL obligations and source/build scripts.
4. Preserve GPL corresponding-source access for *the exact release binary*
   and all modifications; a link to a moving upstream branch is not enough.
5. Check whether **GPLv3-only, GPLv2-only or restricted proprietary**
   components are combined incompatibly; where uncertain, **do not ship**.
6. No Bloodborne game binaries, decrypted game event files, copyright game
   assets, player saves, private account databases, credentials or third-party
   website artwork are redistributed.
7. Mark the project **unofficial and unaffiliated**; do not use another
   author's name as an endorsement.
8. Do not publish or auto-install a player release until the license
   audit **and** real native client/server/network test gates are passed.

## Correction and takedown process

Maintainers welcome evidence of missing attribution or licensing mistakes.
Provide the source URL, pinned revision, file and claimed license/author.
Temporarily quarantine disputed imports while investigating rather than
assuming public GitHub visibility grants redistribution rights. No blanket
statement that \"everything was licensed correctly\" is warranted without
reviewing the shipped bill of materials.
