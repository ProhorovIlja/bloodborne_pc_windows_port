# Bloodborne for Windows: PS4 compatibility runtime vs **actual** PC source port

**Architecture correction, 2026-10-31.** The target is a Windows-native Bloodborne game **comparable in architecture to the PC edition of Dark Souls III**, not merely original PS4 CPU instructions executing directly on an x86-64 PC. Earlier project text used "native Windows port" too broadly. Do not call a green packaging check, native CPU execution, PS4 ELF hash match, or a working Vulkan compatibility layer a completed true Windows source port.

## Verified facts, not marketing labels

| Component / project | What actually runs | Need retail PS4 executable or derived image to play? | PS4 platform ABI/runtime? | Has a complete Windows-native game executable? |
| --- | --- | --- | --- | --- |
| Dark Souls III PC (user-owned `DarkSoulsIII.exe`) | Windows PE32+ x86-64 image (Machine 0x8664, GUI subsystem), importing `KERNEL32.dll`, `USER32.dll`, `d3d11.dll`, `dxgi.dll`, `XINPUT1_3.dll` etc. | No | No PS4 ABI required | Yes, Windows PC release |
| `deadinside28/bloodborne_pc` / bbport and Windows CLS v0.1.3 | Original Bloodborne 1.09 PS4 executable's x86-64 game machine code, converted into loadable memory image, under a Windows native compatibility host | **Yes** | **Yes**: PS4 libc/OS functions reimplemented; Vulkan renderer/shader translation derived from shadPS4 | **No.** `Bloodborne.exe` is a PE *host/launcher* for PS4 game code, not a source-rebuilt Windows Bloodborne |
| `Awakenchan/LanternEngine`, `droogie/bbhost`, `Supermedo/bloodborne_pc` | Original PS4 game code plus modified PS4 ABI and graphics translation mechanisms | **Yes** | **Yes**, in varying degrees | **No** by this strict definition |
| `Yharnam-Hunters/Paleblood` | **Work in progress**: verified game functions rewritten as C/C++; existing PS4 ELF still used as reference and for temporary host scaffold | **Today: yes**; eventual goal: no | Own runtime currently implements part of the PS4 import ABI; long-term aim is native engine-level graphics and no original executable in game run | **Not yet**, project targets Linux in current onboarding |

Sources: `https://github.com/deadinside28/bloodborne_pc/blob/master/README.md`,
`https://github.com/Mrsuss60/bloodborne_pc_windows_port/blob/master/README.md`,
`https://github.com/Awakenchan/LanternEngine/blob/main/README.md`,
`https://github.com/Yharnam-Hunters/Paleblood/blob/main/README.md` and
`docs/ARCHITECTURE.md` in that repository. This matrix is a **source review**, not a new user-game execution test.

From the user's PRIVATE Google Drive, an offline PE header/import-table read of the **actual** 88,753,416-byte `DarkSoulsIII.exe` confirmed PE32+ x86-64 (Windows GUI) and imports listed above. Separately, the user's 1.09 Bloodborne `eboot.bin-decrypted` is PS4 SCE ELF64 x86-64 with clean loaded-image reference SHA-256 `071df19c8880086d97182dbc057bc8cb37badaca57d9112683836b24a0444c0a`. **Same CPU ISA does not mean same operating-system or GPU ABI.** Neither original executable was uploaded to GitHub.

### The key nuance

Calling bbport "native" is justified **only in the narrow sense of native CPU execution without CPU instruction emulation or JIT**. Its public maintainers compare it to Wine + DXVK for **a single PS4 game**: a title-specific runtime supplies former PS4 system functions and a Vulkan renderer translates GPU work. No complete PS4 console needs to be emulated, but the original PS4 game and compatibility interfaces remain essential. This is **not** the source-recompiled Windows engine port requested by the project owner.

`Bloodborne.exe` having a Windows PE header establishes the **host executable's** format, not the linked game's provenance. Similarly, hash-checking the PS4 1.09 executable shows only version/patch compatibility and must not be presented as progress toward removing PS4 runtime dependencies.

## Current honest full-source-port status (2026-10-31)

`Yharnam-Hunters/Paleblood` main (verified directly from its README and STATUS):
- 157,757 Ghidra-listed functions in the target, 53 replaced and edge-verified, **21 fully verified (0.01%)** as of the checked main;
- 252/686 PS4 runtime system imports implemented (219 by the game's own modules and 33 by project runtime), **430 unbound**, with 4 diagnostics;
- its **own** runtime stops boot at `scePthreadAttrGetaffinity`, milestone 0/8;
- the existing playable test scaffold still comes from an external compatibility host;
- no finished Windows-native game port, no built complete original-free game client.

This is the closest located **decompilation/source reconstruction** effort, **not** a production-ready PC source port. Its public build and onboarding are currently Linux-focused. The recovered Dark Souls III PC executable can be useful for identifying general FromSoftware-era Windows engine interfaces, but **cannot be transplanted** as Bloodborne game source or assumed to share exact symbols and game systems.

## Acceptance gates for the **requested** Windows-native game

- **No PS4 executable/code dependency for playing:** launch the finished Windows PE game built/recompiled for Windows; runtime launch must NOT load or execute `eboot.bin`, a flat image derived from it, or PS4 ELF modules. The original executable may be used only in separate, private *verification* workflows.
- **Native systems:** gameplay/engine logic is rebuilt/recompiled, and process/threading, files, input/controller, audio, networking and graphics use Windows or cross-platform native APIs. No guest PS4 kernel/system-call shim needed in final runtime.
- **Native GPU:** render at engine/draw level to Vulkan/D3D12 instead of processing PS4 GNM/GCN guest command streams at runtime; translated shaders can be a build-time artifact if legal/verified.
- **Legitimate original data:** private game assets may remain in their original formats and be read by native loaders; proprietary assets are never committed or redistributed. PS4-origin assets alone do not make a PC executable into a compatibility layer.
- **Functional full game:** menus, saves, progression, bosses, DLC, cutscenes, sound, input, graphics, performance, long sessions, mods, updates; actual Windows gameplay test evidence required.
- **Online integrated:** Yharnam Together client + 5-seat authoritative state + secure Direct P2P for eligible high-frequency traffic, WAN/NAT testing, invaders, DBNO, host migration/reconnect when specified; >=99% 200-player Qt delivery threshold only after real measured evidence.
- **Proof:** CI must label each achieved gate precisely. Passing C++ compilation of a compatibility host, native PE file checks, or an ELF image hash **must never mark the Windows source port completed**.

## Development tracks, deliberately not conflated

1. **Existing playable compatibility-host research** (bbport/CLS, our Draft #61/#72/#73/#75/#76): useful to test gameplay semantics, renderer behavior, seamless online, network protocol, server performance and reverse-engineering evidence. It is a temporary technical reference **not the requested final port**.
2. **Actual Windows-native engine/source reconstruction** (Paleblood-like verified decompilation, usable native library code and safe reusable data readers): source reconstruction, native Windows platform interfaces, engine-level graphics, integrated gameplay and co-op, independent test cases. Prioritize high-leverage engine/platform subsystems over random function ports. Keep independent licensing and attribution; do not claim full-port progress until genuinely eliminating runtime PS4 dependencies.

**Current result:** true Windows-native Bloodborne with all of these properties **has not been demonstrated** in any checked public source or this project's CI. The problem remains substantial. Do not promise a timeline, a ready artifact, or imply otherwise.
