# Credits, provenance and acknowledgements

**Seamless Hunt: Bloodborne PC is a community-developed, modified downstream
build of Yharnam Together.** It is not a rebrand of other people's work as our
own. The game, launcher, online systems, backend, graphics and patches build on
many independent contributors. Their original copyright, licenses, authorship
and revision histories remain theirs.

This page distinguishes **included upstream components**, **changes developed
in this downstream**, **inherited upstream acknowledgements**, and **projects
only under consideration**. Mention here does not imply an endorsement,
permission outside an actual license, or a contribution to this fork.

## Actual primary source and pinned provenance

| Component | Attribution | How it enters Seamless Hunt |
| --- | --- | --- |
| [Yharnam Together / Bloodborne Seamless Co-op](https://github.com/lKaniel/bloodborne-server), maintained by the upstream team | **Primary engine, BLauncher, co-op client, event patch scripts and Qt shadNet backend**. We retain its license, existing copyright notices, README credits, and commit attribution. | Fetched at upstream commit [`77e350743a7c...`](https://github.com/lKaniel/bloodborne-server/commit/77e350743a7cb4524cfcc1782fb6e3af64e25b15) (v1.1.9) in CI; original sources are modified by independently auditable source overlays. v1.2.0 improvements are **not yet merged**. |
| [shadPS4](https://github.com/shadps4-emu/shadPS4) contributors | Shader recompiler, graphics renderer and other code integrated into the *upstream* native game/runtime. | Inherited through Yharnam Together; no claim to original authorship. |
| [Wozzardman/shadp2p](https://github.com/Wozzardman/shadp2p) | Earlier shadPS4 P2P networking / Bloodborne co-op ancestry. | Credited by Yharnam Together upstream. |
| [Wozzardman/shadnet-p2p](https://github.com/Wozzardman/shadnet-p2p) and the shadPS4 networking team | shadNet networking server ancestry. | Credited by Yharnam Together; Qt-based server carries our optional overlays. |
| [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc) | Linux-native Bloodborne PC port foundation. | Already integrated by Yharnam Together; the legacy `master` branch also originates from earlier native-port work. |
| [Supermedo/bloodborne_pc](https://github.com/Supermedo/bloodborne_pc) and Mohammed Albarghouthi | Windows-native port, launcher and graphics functionality. | Included in Yharnam Together's upstream history, not independently copied as a new launcher. |
| [0xCydral/bloodborne_pc](https://github.com/0xCydral/bloodborne_pc) (previously AdrianCsT) | Revised Windows launcher, PKG workflow, frame generation, XeSS, ReShade and input fixes. | Credited in Yharnam Together's upstream lineage; Seamless Hunt uses its upstream **BLauncher**, not a separate Visy launcher. |
| [Bloodborne PC Online](https://github.com/lKaniel/bloodborne-server) community backend and [The Hunter's Dream](https://thehuntersdream.com), by droogie | Online-services behavior and service layout acknowledged by upstream. | Backend heritage/reference. This does **not** imply copying the site's proprietary assets or live player data. |
| Kyo, [Lance McDonald](https://github.com/LanceMcDonald), auser1337, illusion, emoose and other Bloodborne patch contributors | Bloodborne 1.09 community patch research. | Acknowledged by upstream in `bbport/patches/Bloodborne.xml`; preserve per-patch notices and author tags. |
| [LukeYui's Elden Ring Seamless Co-op](https://www.nexusmods.com/eldenring/mods/510) and Elden Ring Nightreign | Co-op and party-death **design inspirations** listed by upstream. | **No code provenance is claimed** from these projects. |

## Seamless Hunt modifications (not upstream endorsements)

This downstream maintains separate source-checked experimental overlays for
native client stability (bounded Vulkan resource use, long-session diagnostics,
Quit to Desktop, optional spectator camera), co-op gameplay, account and network
defenses, native Windows/Ubuntu Qt 6.8.3 staging, package safety, and update
channel isolation. Patches include work adapted from earlier **internal**
development and reusable diagnostics in the same account's Tekken 6 experiment.
Upstream authorship and all license obligations are preserved. A passing source
test is **not proof of gameplay or online interoperability**.

The maintained development branch is
[`feature/seamless-hunt-mainline`](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/tree/feature/seamless-hunt-mainline).
The historical repository root, older branches, original `master` client
and its launcher are separate references, **not** this candidate's engine or GUI.

## Other projects being evaluated, not automatically included

[Visy](https://github.com/search?q=Visy+Bloodborne&type=repositories),
[BBHost](https://github.com/search?q=BBHost+Bloodborne&type=repositories),
newer deadinside28 and Supermedo forks, newer shadPS4/shadNet,
[FireBurn/FSR-Vulkan](https://github.com/FireBurn/FSR-Vulkan), CLS seamless-co-op
and any projects by other community developers are **research candidates**.
Listing them here does **not** mean their latest code has been copied,
ported, licensed for redistribution or shipped. Some, such as FireBurn's
FSR-Vulkan, are **already present inside the upstream baseline**; others are
not. Each new import must be independently audited.

### Additional co-op projects researched, **not imported**

- [Visy: native Windows Bloodborne co-op](https://github.com/visy/bloodborne_pc_windows_port)
  documents an independently developed direct-party implementation,
  GPLv3, and describes LukeYui's Seamless Co-op as a **design reference**.
  We have **not** imported Visy's latest co-op code.
- [Nightwatch Co-op](https://github.com/vladtepes22/NightwatchCoop)
  expressly credits its combination of **Awaken/Lantern Engine** with
  Visy's co-op. Its GPLv3 license and Lantern Engine's separate
  `NOTICE` impose attribution conditions that require their own review.
  No Nightwatch files have been incorporated into this mainline.
- [CLS BBSC](https://github.com/CLSAMG22/BBSC), by CLS_AMG, is a
  separate network/co-op implementation and an **interop target**, not
  proof of shared client protocol or a copied source dependency.

This is an **acknowledgement of independent projects, not an accusation**
of plagiarism or an endorsement. Similar seamless gameplay concepts do
not establish common source-code ancestry. Any future inclusion must be
reviewed under its exact license and credited to its actual authors.

## Important third-party components and runtime dependencies

The Yharnam Together Windows bundle stages separate notices/licenses for
[FireBurn/FSR-Vulkan](https://github.com/FireBurn/FSR-Vulkan),
AMD FidelityFX SDK, [Dear ImGui](https://github.com/ocornut/imgui),
[LibAtrac9](https://github.com/Thealexbarney/LibAtrac9),
Intel XeSS, NVIDIA DLSS, Qt 6, ReShade, [PkgTool/LibOrbisPkg](https://github.com/maxton/LibOrbisPkg),
and the CLANG64/MSYS2 libraries actually bundled, among others. **Their
different license conditions continue to apply**. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the upstream
[launcher/server credits](https://github.com/lKaniel/bloodborne-server#credits-and-forks)
and [native port credits](https://github.com/lKaniel/bloodborne-server/blob/main/bbport/README.md#credits-and-licenses).

## Rights and attribution

- **Public on GitHub is not the same as permissively licensed.** Verify an
  explicit license at the **specific fetched revision** before reuse.
- Do not delete, rewrite, conceal or falsely transfer original copyright.
  Keep the original complete license and upstream notices beside binaries.
- Upstream Yharnam Together says **GPL-2.0-or-later**. The current repository
  root has a **GPLv3** text from the older repository. This does **not**
  replace per-file licenses or automatically relicense upstream code.
  A combined-release compatibility and corresponding-source audit is
  mandatory; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- No proprietary Bloodborne game executable, event archives, save data or
  assets may be distributed by this project. Users provide their own game.
- All marks remain the property of their respective holders. Seamless Hunt
  is an **unofficial community project**, not affiliated with, endorsed,
  sponsored or maintained by Sony Interactive Entertainment, FromSoftware,
  the Yharnam Together developers or the other credited contributors.

If we missed an author, a copyright notice, a license or a provenance link,
please open a GitHub issue or pull request with the **source URL, path, revision
and correct attribution**. We will correct the record; we will not
misrepresent projects or present third-party work as originally ours.
