# V206: REAL Bloodborne 1.09 Windows-native import subsystem audit

**Evidence source:** the user's private decrypted original Bloodborne
ELF64 x86-64, `eboot.bin-decrypted`, from their connected
`CUSA03173` Drive folder. The original executable stayed outside
GitHub. Original package `param.sfo` says APP_VER 01.09.

This is a reproducible full-original-game import profile, not an
analysis of artificial x86 functions. The analysis script
`profile_private_original_imports_v206.py` uses only Python stdlib,
reads the original PS4 dynlib/symbol/relocation tables privately
and emits AGGREGATED public SDK library counts, not code, addresses,
original NIDs, user data or private game files.

## Verified direct original-game measurements

- Original PS4 dynamic libraries: **43**.
- Original PS4 dynamic modules: **43**.
- Original dynamic symbols: **703**.
- Real import relocations: **684** total,
  **661** `R_X86_64_JUMP_SLOT` +
  **23** `R_X86_64_GLOB_DAT`.
- Every import relocation's original symbol library AND original
  module IDs were resolved. **0 unknown import relocation slots**.

| Windows-native subsystem replacement family | Actual imported slots |
| --- | ---: |
| C/C++ runtime, Win32 kernel, threading, clock | **321** |
| Network, HTTP, TLS sockets | **67** |
| Rendering, video output and frame presentation | **58** |
| Audio output/input, voice, movie decoder | **48** |
| Game assets, filesystem/streaming, save data | **40** |
| Input devices, mouse and IME | **18** |
| Online account, co-op matchmaking and social | **113** |
| Other platform/system services | **19** |
| **All imported function/data slots** | **684** |

This is an import **inventory**, not a complete function
implementation count. A single import can require extensive
Windows-native behavior (especially GNM GPU, networking and Fios).
And static in-game functions may depend on hardware semantics
without any imported SDK call.

Highest volumes: libc **200**, libkernel **79**,
libSceGnmDriver **50**, libSceNet **35**, libScePosix **32**,
libSceNpMatching2 **27**, libSceHttp **24**,
libSceNpManager **20**, libSceFios2 **17**,
libSceNpWebApi **17**, libSceAvPlayer **16**,
libSceNpScore **14**.

## What the profile changes in engineering priorities

1. **Original image loader and native Windows ABI shim:** import
   address map and authentic functions' original calling semantics;
   timer, memory allocators, TLS, synchronization and exception
   semantics. Use real Win32/CRT equivalents, not a PS4 kernel.
2. **Renderer and GPU memory model:** 50 GNM driver imports plus
   video output. Native Vulkan/D3D12 rendering is a large separate
   engineering effort. A compiled CPU function library is not
   sufficient for a visible game.
3. **Asset IO and save:** Fios, SaveData and GameContent, with
   imported real Bloodborne `dvdroot_ps4` and PC-safe paths.
4. **Game and network services:** keep standalone/offline startup
   independent of PSN, then connect Yharnam Together's own services
   without putting the original PS4 NP emulator back into the
   finished Windows game. Online import references are not
   equivalent to direct game P2P.
5. **Input/audio/video and UI:** PS4 Pad/IME, AudioOut/AJM,
   AvPlayer, user dialogs and launch/settings integration.
6. Build and boot with the **real private full game's original
   EBOOT as build-time input only**; the resulting native game
   must not depend on that original ELF at runtime.

Existing V204 private original whole-image Zydis scanner and AOT
generator still need to run successfully end-to-end. This
environment could inspect the original ELF but cannot fetch a
working original source-pinned Zydis toolchain via container git
network DNS; therefore **no complete original game recompilation
or native Bloodborne.exe boot was performed**. The separate
Yharnam Together playable source work is PR #85.

Run this profile privately:

    python3 native/source-port/recomp-v194/profile_private_original_imports_v206.py --decrypted-elf /private/Bloodborne/CUSA03173/eboot.bin-decrypted

Never upload private input, generated C, objects or original executable
to GitHub/Actions. PR #84 stays draft, production Fornex/YT untouched.
