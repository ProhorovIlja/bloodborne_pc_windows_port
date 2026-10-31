# V186: Native PC asset subsystem, not a PS4 compatibility host

This source library is **genuine compiled C++20 code that can run on Windows** and independently reads FromSoftware's **asset container data**. It has no ELF loader, PS4 system calls, GNM, PS4 command processor, guest machine image, Vulkan translation, account, secrets, or gameplay hooks. It cannot run Bloodborne on its own. It is a small **building block** of the requested, independently compiled Windows source port. The native engine must eventually use Windows/cross-platform OS, input, audio, rendering and networking interfaces, not execute `eboot.bin` or an equivalent PS4 image.

## Original private-game validation (performed locally; game bytes not in repo)

Read-only original files from user's private Google Drive on 2026-10-31. The same **DCX DFLT / BND4** container structure and BND4 virtual names exist in both games, but the payload sizes and executable/platform ABIs are not interchangeable:

| Private source | DCX bytes | BND4 decompressed bytes | Entries | Combined uncompressed member bytes |
|---|---:|---:|---:|---:|
| Bloodborne 1.09 `dvdroot_ps4/shader/gxshader.shaderbnd.dcx` | 3,496 | 10,028 | 15 | 8,488 |
| Dark Souls III PC `shader/gxshader.shaderbnd.dcx` | 3,024 | 15,204 | 15 | not essential to compare |
| Bloodborne 1.09 `dvdroot_ps4/shader/gxgui.shaderbnd.dcx` | 2,737 | 9,044 | 13 | 7,804 |
| Dark Souls III PC `shader/gxgui.shaderbnd.dcx` | 2,640 | 17,232 | 13 | not essential to compare |
| Bloodborne 1.09 `dvdroot_ps4/script/eventcommon.luabnd.dcx` | 29,935 | 147,296 | 3 | 146,721 |

All **15/15** shader names and **13/13** GUI shader names match between games, but **15/15** and **13/13**, respectively, have different member byte sizes. That is *not* proof of compatible shader bytecode, GX layouts, game logic or rendering. The private original contents were not copied, published or committed.

**Source-driven bug fixed on actual files:** Dark Souls III aligns DCX-DFLT streams to 16-byte boundaries using 0–15 **zero padding bytes**, while sampled Bloodborne DCXs end at the zlib stream. V186 accepts only up to 15 strictly zero bytes after the exact stored compressed size, rejects all nonzero extra bytes, and uses a bounded zlib inflate. Both original games pass. This matters for native asset loading in the future.

V186 currently accepts only **little-endian** BND4 with 0x24 entry headers, UTF-16LE names and the observed 0x54/0x74 formats; it rejects other variants rather than guessing. It verifies all member offsets/sizes, supports zlib-compressed members and returns bytes **only in memory**. No game assets are written or extracted. Additional formats (BXF, TPF, PARAM, FLVER, MSB, EMEVD, shader representation) require separate independently verified readers. Game materials can be reused **as private asset data** by a true Windows-native game engine, whereas the final Windows game process must not execute the PS4 ELF.

## Sources, license, and cross-project boundary

- BND4/DCX container layout cross-checked with SoulsFormats public code (JKAnderson/SoulsFormats, its upstream license applies to its code; V186 is written independently as a small new parser using documented file format structure).
- `droogie/bbhost` uses GX engine-level render records, progressively replaced game code and a native Vulkan path; still relies on PS4 ELF. Its `docs/decomp.md` currently reports 200 source-rewritten functions, with its own testing criteria. Its PS4 HLE and shader translation **cannot be labelled** complete Windows-native source port.
- `Awakenchan/LanternEngine`, `deadinside28/bloodborne_pc`, `Supermedo/bloodborne_pc`, `visy/bloodborne_pc_windows_port`, `droogie/bbhost` and `lKaniel/bloodborne-server` are invaluable for GPU/UX, feature semantics and networking, but all retain source PS4 game code execution.
- `Yharnam-Hunters/Paleblood` is an explicit source-reconstruction effort: 21 fully verified functions of 157,757 in the checked 2026-10-31 README (a different metric/standard from bbhost's 200 rewritten). Its own runtime is not yet a playable full-game Windows executable.
- The user's **actual** Windows `DarkSoulsIII.exe` is PE32+ AMD64 and imports Win32/D3D11. It is a PC-engine/platform reference, not ready-made Bloodborne game source.
- The Yharnam Together server, client design and 5-seat gameplay/network work can be integrated after the native game engine exists. Native multiplayer cannot be independently accepted from V186 parser tests.

Source checkout scope: this project is GPL-2.0-or-later. Where donor source is GPL-3.0-or-later, do not copy it into a GPL-2.0-only subtree without a compatible whole-program licensing review. This patch does not copy any donor source or user retail data.

### Reproduce with private game files only (not CI)

```sh
cmake -S native/source-port/assets -B build/native-assets -DCMAKE_BUILD_TYPE=Release
cmake --build build/native-assets --parallel 4
ctest --test-dir build/native-assets --output-on-failure
build/native-assets/bb-native-assets /private/Bloodborne/dvdroot_ps4/shader/gxshader.shaderbnd.dcx /private/DS3/shader/gxshader.shaderbnd.dcx
```

The output is **aggregate counts only**, never full virtual names or private paths. The public CI uses synthetic in-memory DCX/BND4 only. Runtime verification with the private original assets is deliberately outside GitHub Actions.

**Next genuine source-port gates:** generic asset VFS and controlled readers (BND4/BXF, PARAM, FLVER, event scripts), native engine logic and scene state, GX-level renderer against cross-validated DS3 Windows behavior and bbhost's documented intermediate model, independent Windows audio/input/files/network, verified replacement gameplay functions and full-game boot **without any PS4 ELF image**. Green V186 means **just a native asset reader**.
