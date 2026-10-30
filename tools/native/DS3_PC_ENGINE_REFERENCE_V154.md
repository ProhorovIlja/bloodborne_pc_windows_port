# Dark Souls III as a PC-native reference for Yharnam Together / Bloodborne

Status: **research / input characterization**, no game-code import and no claim of identical versions.

## Why DS3 matters

Lance McDonald stated in [PC Gamer](https://www.pcgamer.com/meet-the-dark-souls-detective-uncovering-lothrics-cut-content/) that DS3 uses a fork of an early Bloodborne engine and many map formats transfer. This is practitioner evidence, not official FromSoftware source provenance. [bbhost's renderer design](https://github.com/droogie/bbhost/blob/master/docs/rendering.md) documents a concrete translation strategy: From's GX engine interface targets PS4 GNM/PM4+GCN in Bloodborne, but DX11 on DS3 PC. Reconstruct GX operation semantics and bind them to Vulkan rather than replaying PS4 command packets. It is a **reference for graphics architecture**, not an interchangeable DLL or game executable.

The independent [DS3 Codex](https://www.fig14.com/ds3/) reconstructs Firelink Shrine and Cemetery of Ash in native C++/SDL3/Vulkan and [documents actual DX11 captures](https://www.fig14.com/ds3/rendering.html) and [DS3 archives](https://www.fig14.com/ds3/files.html). Its observed DS3 passes: shadow map, six-target G-buffer, SSAO/lights, fog, transparent geometry, YEBIS2 post-processing and anti-aliasing. DS3's actual shader files use DXBC under `shaderbdle.shaderbdlebnd`; some post-processing shaders are embedded in its executable. This **does not prove Bloodborne uses precisely the same G-buffer or shaders**: benchmark independently and adapt only proved shared GX concepts.

## Prioritized investigations with DS3 as reference

1. **High: GX engine abstraction vs console command stream.** Compare DS3 PC resource creation, draw/dispatch, shader binding, resource lifetime and clear/copy ordering to Bloodborne's GX- and GNM-derived renderer. Use bbhost's source and unit/capture tests first. We do not aim to ship DS3's renderer in Bloodborne, nor to bolt DS3's D3D11 DLL onto the YT runtime. Confirm Vulkan validation and present/capture parity before measuring CPU or GPU speedups.
2. **High: shaders/materials and PC post-processing.** Compare naming and interfaces of DS3 DXBC and available Bloodborne GPU programs, especially MTD/GX constants, vertex layouts, textures, instancing, LOD, SSAO, depth of field and tonemapping. The DS3 Codex supplies known-good PC frame pipeline examples, not drop-in proprietary shader binaries.
3. **High: shared FromSoft asset formats.** Reuse public [SoulsFormatsNEXT](https://github.com/soulsmods/SoulsFormatsNEXT), [WitchyBND](https://github.com/ividyon/WitchyBND), Smithbox/Paramdex and DarkScript where actually compatible. Format families: FLVER models, BND4/DCX containers, MSB map placement, EMEVD events, ESD dialogs, PARAM gameplay, TAE animation events, TPF textures, Havok HKX. Version/layout differences require game-specific adapters, field checks and golden fixtures.
4. **Medium: physics/animation/multiplayer progression.** DS3 can explain engine concepts (Havok constraints, events, animation synchronization, co-op state machine), but the PS4 Bloodborne gameplay rules, guest save progression, DBNO, five player seats and authenticated YT Protocol8 remain authoritative. DS3 network packets, Steam login and invasions cannot be substituted for our protocol or server grants.
5. **Medium: native Windows ergonomics.** Compare PC frame pacing, input/alt-tab, device reset, sound, saves, controller rebinding, window handling. Implement native host APIs in the YT Windows runtime where correct without breaking the guest ABI expected by the original Bloodborne x86-64 code.

## What DS3 files actually help

The DS3 PC Steam `Game/` directory is the useful reference. Its `DarkSoulsIII.exe` is a native x64 Windows PE and its assets are usually sealed into `Data0-5.bdt` alongside `.bhd` indices. An extension inventory of visible disk files **does not enumerate the FLVER/EMEVD/FXR/GX shader files INSIDE those archives**. A legitimate offline extraction and metadata-only parser will be a separate step, never an automated public CI download.

**Do not upload a second 20-30GB game archive just to begin.** Existing DS3 Codex and public parsers already document enough to start graphics source comparison. If local cross-title confirmation is needed later, produce metadata-only inventories, format/schema versions, anonymized aggregated shader/pass counts and scrubbed timing traces. Do not publish either game's EXE, archive, extracted shaders, keys or saves in GitHub Actions or a public repository.

## Gates: do not conflate understanding with an achieved native PC port

- Source citation and licensing/provenance for each GX/asset observation.
- Run same scenes/inputs in a real user-owned DS3 PC copy when needed; never compare DS3 FPS to Bloodborne FPS as though game content were identical.
- On original YT1.3 Windows, compare GPU resource use, C++ frame capture, CI compiler status and actual gameplay. **No performance claim until measured**.
- Preserve YT Protocol8 server authority, reliable/unreliable transport split and encrypted Direct P2P grant/fallback rules; do not switch to DS3 Steam netcode.
- In the long term some PS4-designed ABI and GPU-origin formats remain in the closed-source Bloodborne game code even when executed natively without a PS4 emulator; completely replacing proprietary gameplay logic is a separate engine-reimplementation effort.
