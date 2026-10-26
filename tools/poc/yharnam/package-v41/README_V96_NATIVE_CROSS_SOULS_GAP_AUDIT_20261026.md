# V96 native Bloodborne / Souls co-op cross-repo gap audit
2026-10-26 | source-only development PR20 | no Fornex/master/account/save mutation

"Upstream implemented" DOES NOT establish compiled in our hybrid client. A passed CI source test is NOT a two-PC gameplay run. All candidate changes need a version/protocol and license audit.

## Shipped source adaptation: V96 HudSight stability

Yharnam Together PR418 (https://github.com/lKaniel/bloodborne-server/pull/418) reports 10 repeated Windows startup crashes with the VK_LAYER_HudSight2 implicit Vulkan overlay in the device and XeSS dispatch chain. Our pinned upstream commit 77e3507 lacks its new launcher fix.

V96 patch_vk_layer_compat_v96.py source-checks the pinned native bbport/launcher/bbport_launcher_win.py and adds a per-game-process VK_LOADER_LAYERS_DISABLE glob for HudSight only, preserving inherited disabled layers without duplicates, while advanced extra_env remains authoritative. No system-wide environment change, no blanket ReShade, MangoHud or Steam layer block, no injected runtime hook. Staged in original native Windows source package; separate Python tests and actual pinned-source Windows/Linux CI.

## P0: must be correct before release

1. Native Windows bootable package: PR20 V65 corrects real FidelityFX _countof compile failure; V95 adds local exact Blood Level (BL) + stat-derived weapon-build preview and safe Quit from the in-game Co-op Team menu; V96 adds pinned HudSight guard. These are not a working EXE until actual full renderer/game loader compiles, links, ships and is run with a real game dump.
2. Multi-hour performance: track GPU texture and render-target VRAM growth, pipeline/shader caches, orphan host game threads, thread count, memory fragmentation, frame pacing, p95/p99 game-frame time for 30/60/120 minute sessions. Mrsuss60 v0.6.1 records startup thread heap crash, mid-game texture streaming memcpy, Central Yharnam Vulkan device loss and Ebrietas high-FPS worker problems; visy documents idle depth-target VRAM growth and earlier severe party-mode FPS drops. Diff pinned source first because some fixes might already be present. References https://github.com/Mrsuss60/bloodborne_pc_windows_port/releases and https://github.com/visy/bloodborne_pc_windows_port/releases .
3. Save security: original pinned Yharnam Together already has StartSaveBackups and ParseSaveBackups with off/0 opt-out and BackUpSaves/PruneSaveBackups in emulator/src/core/bloodborne_patches.cpp and bloodborne_party.cpp. DO NOT add a competing blind backup timer. Prove that the native shipped game actually invokes it, snapshots are atomic, restorable and isolated by character/world, add explicit pre-party recoverable snapshot and no-loss-after-NG+ checks. visy's party-save undo and separate ERSC saves offer acceptance test ideas, not drop-in code.
4. Crash-reconnect/host migration: hard-crash host, 5/20/180 s network loss, rejoin with same save, quit during Chalice or boss, prevent duplicate rewards and stale avatars, server-owned world revision and migration epoch, no phantom or ghost control after world reset. Yharnam PR403 (host takeover), PR412 (leave/remove grace), visy v0.7.4 and v0.7.5 are practical references.
5. Direct gameplay P2P still UNIMPLEMENTED: V84–V93 signed TLS and same-socket NAT test cannot safely route GameLink gameplay. Need true AEAD game datagrams, both-way verified NAT endpoint updates, ack+seq atomic ownership handover, reliable relay failback, CGNAT/WARP fallback, authorized session changes, 2 real Windows PCs. Measure CPU, memory, bytes and latency under ~200 players/100 parties before any reduced-server-load claim.

## P1: gameplay and co-op bug classes with public evidence

- Death, revive and spectator: Yharnam PR397 team opt-in spectate/freecam and boss spectate extension PR414; PR410 removes lethal catches while dead; PR413 removes stale remote-target death bit after revival; draft PR411 handles out-of-order delayed wipe while teammates already respawned. Test boss, fall, lamp, disconnect while down, 3-4 hunters. Never copy a UI camera patch without related server/game hooks.
- Quest and world state: PR407 Doll flag 6700 is per-player; PR408 single boss owner; PR409 story Chalice reward; PR405 map-generator enemies; PR406 unique quest items. visy v0.7.5 independently describes item/shops, lamps, elevators, Cainhurst and Chalice failures fixed by session-scoped state and proper recipient authority. Avoid replaying one-time items into saves.
- Multiplayer rules: synchronized host scaling, rot, travel vote, death mode and invasion/PvP opt-in. Danger: user-specific save flags versus shared server-owned flags. No silent default difficulty, forced invasion or changing vanilla offline play.
- Player-experience fixes: fall-revive camera orientation, switch living spectate targets, freecam key rebinding, accurate network/join/error status, missing DLC/chalice eligibility, late guest joins, no guest sent to Hunter's Dream after border crossing.
- Three-player VPN/NAT: visy v0.7.5 documents auto LAN/Radmin/Hamachi/Tailscale discovery, stale same-private-IP peers and Cloudflare WARP failures. Native Yharnam needs diagnostic difference between relay and direct, IP visibility consent, signed candidate lifecycle; do not assume its alternate protocol can be imported into original shadNet.

## P1: native GPU, launcher and Discord

- Run V96 HudSight Vulkan crash layer guard through pinned native launcher only; keep user advanced environment override.
- Add game-native CPU/GPU/VRAM/thread/ring-buffer performance snapshots and support bundles with secret redaction (password, joining tokens, NAT candidates). Crash reports should identify module, GPU, game patch, driver and source provenance; no private user IDs by default.
- Adopt upstream PR419 co-op setup in 3 clear steps only after verifying user-facing setup and existing settings mapping. Never bundle new DB schema and network wire fields from PR412 without a coordinated release and rollback.
- V95 truly reads Blood Level, not inferred sum, and labels weapon-stat combinations when an offensive stat >=18 (STR/SKL/BLT/ARC). Existing implementation shows local read-only preview. STILL MISSING: actual native Discord RPC bridge with explicit user consent and independent level/build visibility, rate-limited updates, true online area, team counts, expiring server-authorized Join secret. Never publish private peer IP/password/master; clear status on logout/exit.
- Native in-game Quit exists in settings and V95 adds direct Co-op Team button using existing Cancel-default SDL quit. Real client click and multiplayer clean shutdown test remains unverified.
- Test modes: ultrawide UI, low VRAM, bad dump, GPU selection, exotic Vulkan layers, FSR fallback and >60FPS boss worker effects. Do not promise universal FPS/FSR 4 on all hardware until shader tests.

## Other Souls titles: independent design, not code mixing

- Elden Ring Seamless Co-op, https://www.nexusmods.com/eldenring/mods/510 : session persists after death/boss, world/waypoints/NPC events sync, all players remain, separate saves, transport based on Steam networking. None of that transport can simply replace original Qt shadNet identities.
- Sekiro Online, https://www.nexusmods.com/sekiro/mods/577 : peer gameplay and server for summons, prediction improves perceived PvE responsiveness. Do not predict authoritative Bloodborne boss state without deterministic proof.
- Open source sekiro-coop prototype, https://github.com/mstampfli/sekiro-coop : separate authority/rollback/network/reliability packages, twin-game determinism probes and peer simulator. Test-harness ARCHITECTURE is a possible inspiration, not a ready Bloodborne implementation.
- Blue Sentinel for Dark Souls 3, https://github.com/yuiamoroll/Blue-Sentinel-Release : inbound packet validation and anti-abuse principles, useful to test with pre-auth shadNet V94; Blue Sentinel's code is not public and may not be copied/redistributed.
- unseamless-coop Rust ER prototype, https://github.com/micthiesen/unseamless-coop : typed memory/hooks and pure-core tests; compare instrumentation design only, not engine code.

## Practical release gates

Gate A: V96 native launcher CI + full Windows build + game boot + clean save/quit.
Gate B: 2 actual Windows PCs with original authenticated server, cross-area/chalice/boss/guest-loss tests, restore backup proof and 2hr VRAM/CPU trace.
Gate C: real encrypted direct game-UDP handover with server relay fallback, bad NAT and 200-player load test.
Gate D: real Discord Rich Presence privacy/party/join implementation and playtested launcher flows.
Only after these gates explore optional PvP, invasions, website live player map and custom world statistics with privacy controls.

No source adaptation from unrelated ports or Souls mods should be merged solely because its feature list is impressive. Compare actual files and license, dependency and state-ownership requirements first.
