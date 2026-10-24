# Seamless Hunt V13: Spectator Camera during Down / death

Created 2026-10-24. Native Windows Bloodborne PC port, upstream lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15. Developer integration, NOT a tested game executable.

## Source-integrated behavior

Source files: tools/poc/yharnam/spectator-v13/ (native C/C++ code, fail-closed source patcher, CTest). The unified-v9/compose_sources.py applies V13 AFTER V3 UI Scale, V5 DBNO, V7/V10 guarded P2P and V11 title Rejoin.

The existing Windows runtime_camhook.c 1.09 camera hook receives a render-thread spectator snapshot and translates camera pivot and drawn position only, never the local character position/save. It supports following live same-map teammates based on existing party HUD board coords, and a bounded, local Free Cam. On revive or when gameplay/Team/Map/settings menus take over, mode returns to the native camera. Controller-only sessions install the already verified camera hook early, without enabling mouse controls.

Controls: F/Triangle = Follow; F1/Square = toggle Free Camera; A/D or L1/R1 = select live hunter in Follow. In Free Camera WASD+mouse or left stick+right stick, Space/Ctrl (or Dpad up/down) vertical, Shift (or R2) speed. Original Circle give-up DBNO remains untouched. The existing independent game's Free camera setting Cross+L3 is not replaced.

Architecture: bbport/gpu/bbcoop/coop.cpp exposes living member xyz from PartyPanel into the existing bbcoop_panel via C ABI, and bbport/gpu/shim/bbport_overlay.cpp handles inputs, name and status. bbport/src/runtime_camhook.c applies camera-only transform behind verified hook bytes. Server network protocol is unchanged. No remote areas loaded, no teleport.

Verified locally: CTest 2/2 native tests (C camera-only mocked object and C++ policy state transitions), Python unittest 4/4 patch-source regression tests. Eight exact patch anchors checked unique against pinned real upstream GitHub source. CI on master shyt-v9-source-gate.yml includes V13 camera native build and composed source validation; no completed remote CI run or Windows game build observed.

Release blockers: build full Windows native BBPort including updated runtime + GPU bridge; test in-game camera validity and mouse/right-stick behavior; down-revive, give-up, wipes, map loads, cross-NAT test clients; avoid collisions/occluded views as necessary. Free Cam currently has no collision detection and is bounded to 45 m; no cross-map spectator. If game signature mismatches the 1.09 hook, spectator should disable instead of writing unknown memory.

Source archive SH-YT-SPECTATOR-CAMERA-V13-20261024.zip SHA256 604c3c20f4668730c8d75116f74d7799d7bd413eb3da0169d2e08a59ff64567c. Local archive patcher's behavior mirrors GitHub's split-inc patcher, source pin applies.

No Fornex/CLS server, DNS, firewall, saved games or installed Windows files modified.