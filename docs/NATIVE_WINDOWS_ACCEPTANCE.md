# Native Bloodborne Windows: release and gameplay acceptance gates (V185)

**Goal:** real x86-64 Bloodborne 1.09 code through bbport's Windows native compatibility runtime and Vulkan renderer, plus the corresponding Yharnam Together native co-op client, shadNet server, and low-cost authenticated Direct P2P path for eligible game traffic. Not a full PS4 console emulator. The runtime still implements the original PS4 game ABI and uses code descended from shadPS4's renderer. This is a technical distinction, not a claim of a ground-up rewritten game.

This is a **release checklist**, not an assertion that production is ready. Always distinguish:
- **Package integrity**: ZIP and extracted directory have correct 64-bit PE launchers / network server, matching SHA-256 of all shipped files, and nested `bin/**` dependencies are present.
- **Native actual boot**: supply your own decrypted, updated Bloodborne 1.09 game and run `Bloodborne.exe` on Windows. V185 cannot do this.
- **Real game co-op**: two actual separate Windows machines, five slots, host/guest join, transitions, boss kills, crashes/restart, DBNO and per-player HUD, invasions. V185 cannot do this.
- **Networking**: direct encrypted P2P path and properly authenticated fallback across NAT and reconnect, without leaking authoritative reliable/world/invite traffic or accepting forged grants; measure bytes/packets on both server and clients. Developer-only #61 is not production-enabled.
- **Performance and endurance**: prolonged gameplay, leak/fps/GPU driver variants, Windows launcher update/reinstall with nested DLL integrity, crash recovery, saved games, mod toggles. Not yet accepted.
- **Capacity**: repeat real Qt/Redis 200-player 40×5 load with coherent producer-to-consumer accounting and at least 99% measured delivery. Existing #72 is still red. Intentional policy filtering must not be counted as loss.

## V185 offline package gate

```sh
python tools/native/native_package_integrity_v185.py /private/path/BBSC-Yharnam-Together-0.1.3.zip \
  --write-manifest /private/evidence/BBSC-0.1.3-manifest.json

python tools/native/native_package_integrity_v185.py /private/path/BBSC-Yharnam-Together-0.1.3.zip \
  --verify-manifest /private/evidence/BBSC-0.1.3-manifest.json

python tools/native/native_package_integrity_v185.py /private/extracted/BBSC-Yharnam-Together-0.1.3 \
  --verify-manifest /private/evidence/BBSC-0.1.3-manifest.json
```

### Optional checks against the user's PRIVATE retail game

The full Bloodborne game **is already available on the user's private Drive**, but game files MUST NOT be committed, uploaded as CI artifacts, or bundled into player releases. Where the private files are accessible on the user's own machine:

```sh
python tools/native/native_package_integrity_v185.py /private/CLS-Windows.zip \
  --game-sfo /private/Bloodborne/sce_sys/param.sfo \
  --game-eboot /private/Bloodborne/eboot.bin-decrypted
```

This validates the real `param.sfo` PSF metadata for `CUSA03173` / `APP_VER 01.09` and verifies only the header of the already-decrypted original game's **PS4 ELF64 x86-64**. The PS4-specific ELF ABI still needs the native bbport compatibility runtime. Neither metadata check decrypts the game, proves game patch offsets, or runs anything; output records only true/false acceptance flags and never prints the original file paths.

In a private dry run on 2026-10-31 the actual Drive game metadata passed both checks. This is **stronger than finding filenames** but still falls short of an executable game boot.

The report printed to stdout contains only a bounded count/fingerprint and explicitly marks boot, NAT, and gameplay tests as **false**. The private manifest contains **relative distribution paths and per-file SHA-256**. Keep it private and separate from the game folder; never commit the result, retail game assets, save files, settings or server credentials to the public repository. The checker never executes game binaries, downloads, extracts, or connects to a server. It refuses retail `eboot.bin` or game asset folders inside the distributable, case-conflicting names, ZIP traversal, symlinks, unexpected architectures, and oversized inputs.

V185 checks the Windows PE machine type of four critical components but **PE64 is not proof that a particular game boots natively**. ShadPS4-derived rendering/runtime libraries also don't automatically make it a full console emulator. Inspect native runtime source and actual host process for the authoritative distinction. ZIP+folder manifests compare the same tree, including nested DLLs from vendors, so a missing FSR/DLSS/XeSS/Qt runtime can be detected if it was included in the release baseline; completeness relative to upstream design requires an independently reviewed build manifest.

## Source selection and compatibility

Pin versions, do not take a random whole-fork overwrite: primary YT 1.3.1 `lKaniel/bloodborne-server`, native-port components `deadinside28/bloodborne_pc` and `Supermedo/bloodborne_pc`, and selectively reviewed bbhost / LanternEngine / shadPS4 renderer code. Track protocol schema, launcher, native executable, and server together. Current CLS v0.1.3 Windows test kit (private Drive + ChatGPT Library, see project handoff) identifies `5d2305ee` upstream, but that package number is **not** YT v1.3.0. Avoid publishing the private CLS archive or distributing copyrighted game assets.

**Important packaging upstream:** `Supermedo/bloodborne_pc` PR #140 fixes nested `bin/**` scanning for package manifests and verifies the frozen launcher dependencies; review for source-exact adaptation before final packaging. Testing against sample ZIP is necessary, not sufficient.

Repo code review: Draft #75 independent, default-off CLS lobby cap; #72 actual 200-player server load evidence; #61 developer-gated Direct signed NAT route; #73 upstream invasion-session membership; #74 bounded GitHub diagnostic responses. No automatic merge and no Fornex deploy until all relevant gates pass.
