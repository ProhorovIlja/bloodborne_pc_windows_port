# Verified Bloodborne PC upstream and fork audit, 2026-10-26

Scope: native Windows, Yharnam Together v1.3.0, server performance and true server-authorized Direct peer gameplay. This is a release/commit/source review, not proof of compatibility or live gameplay.

| Repository | Verified release / upstream | Actual source evidence | Decision |
| --- | --- | --- | --- |
| lKaniel/bloodborne-server | v1.3.0, tag 0645740a33 | Official Windows setup; death spectate/freecam, duels, Doll/boss/respawn, backups, shader cache, encrypted CLIENT-TO-SERVER link | BASE. Do not duplicate upstream changes. |
| Mrsuss60/bloodborne_pc_windows_port | v0.7.0 Oct 24, main HEAD 7b4bb957 Oct 26 | 6efb5ac1 touches src/runtime_memory.c, src/probe.c, Vulkan scheduler; 2083ff8b refactors vk_pipeline_cache/serialization; 466e8e7d edits FSR411/depth resampling | REVIEW narrow allocator/pipeline fixes, A/B render/VRAM test; never import opaque DLSS SDK packages. |
| Supermedo/bloodborne_pc | windows-v1.9.4 Oct 21 | Secure Windows certificate handling, updater retry; v1.9.2 FSR FG VRAM leak/4GB OOM, v1.9.3 reverted renderer regressions | REVIEW individual fixes only; different online implementation. |
| visy/bloodborne_pc_windows_port | v0.7.6 Oct 26, HEAD 88f06059 | docs/party/network_robustness.md documents TCP+UDP host, direct peer UDP hole punch and host relay, simulated lag/outages; docs/party/version_check.md includes game/patch/mod hashes; docs/party/save_safety.md includes pre-session snapshots | USE AS DESIGN REFERENCE, not drop-in YT 1.3 compatible nor verified secure server-mediated Direct P2P. |
| shadps4-emu/shadPS4 | v0.20.0 Oct 14 + Oct 25 prerelease 2cdefaa | GPU, address-space and NP fixes | Only cherry-pick compatible low-level code into native runtime; NEVER depend on emulator. |
| CLSAMG22/BBSC | main 0.0.2 Oct 20; Oct 26 PRs still open (#22, #38, #26, #9) | Guest boss respawn and wipe, revive, communion, controller freecam | Review source and test against v1.3; unmerged PRs NOT shipped. |

Source links:
- https://github.com/lKaniel/bloodborne-server/releases/tag/v1.3.0
- https://github.com/Mrsuss60/bloodborne_pc_windows_port/commit/6efb5ac1e82a7acd32c96ed04c13694a059973a3
- https://github.com/Mrsuss60/bloodborne_pc_windows_port/commit/2083ff8be9dcb7807189994b9c67d667f71f770c
- https://github.com/Supermedo/bloodborne_pc/releases/tag/windows-v1.9.4
- https://github.com/visy/bloodborne_pc_windows_port/releases/tag/v0.7.6
- https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/party/network_robustness.md
- https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/party/save_safety.md
- https://github.com/shadps4-emu/shadPS4/releases/tag/v.0.20.0
- https://github.com/CLSAMG22/BBSC/pulls

Confirmed local clean PR #21 C++ Qt6 11/11 success at https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40363648828.
Legacy PR #20 never produced our own game EXE; last Clang64 reached bloodborne_party_death.cpp undeclared InvaderHandles, a C++ source integration failure.

Load test run 40377321790: original 200-player bbload executed but 0 playing, 0 gameplay packets, 1174 refused Hello attempts, so CPU 4.3% and RSS 27.4 MiB are NOT capacity measurements. Root-cause hypothesis supported by source: server/src/config.cpp default CheckServerBuild=true while bbload.cpp sends build='bbload'; the release fingerprint gate can reject synthetic build identities. This patch adds a private/temporary CheckServerBuild=false strictly for 4-user diagnostic smoke and subsequent 200-user test, while preserving ALL production build checks.

Next after reproducible successful load: measure p50/p99 relay, CPU/RSS, drops; compare server-authorized Direct peer candidate paths against visy's host-relay behavior with authenticated keying, replay/nonce checks, NAT punch, relay fallback. Do not claim Direct gameplay is implemented.

Implementation restrictions: no release bundle or commercial game assets, no production Fornex/CLS Friends, passwords, real player saves, master, firewall or external network load tests.

## Fresh additional source comparison, 26 October
deadinside28/bloodborne_pc official Linux native bbport [0.6](https://github.com/deadinside28/bloodborne_pc/releases/tag/0.6), published October 19: GPU-agnostic new memory/translation model, shadPS4 0.20 network/NP and Seamless Hunt/BBSC co-op; useful source candidate for Windows memory/loader safety, not a native Windows binary drop-in.
droogie/bbhost official [v0.2.21](https://github.com/droogie/bbhost/releases/tag/v0.2.21), published October 26: F10 bottleneck/performance meter and periodic perf summary (GPU/game/draw/renderer/fps cap), Vulkan Radeon depth-layout optimizations (claimed ~15% Radeon 680M), >60fps render job splitting, cheaper particles, and accurate network disconnected-state. Prioritize performance diagnostic and network stale-connection guard; test source relevance, licensing and GPU performance before integration. User-requested genuine Direct peer authority is still NOT shipped by our project.

## Real smoke failure / no invented 200-player capacity
Run [40378390716](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40378390716) with temporary CheckServerBuild=false still produced 4 generated users, 0 playing, 12 refusal attempts and zero gameplay packets. Thus the build-fingerprint mismatch was not sufficient to explain all rejections. The original bbload executable writes explicit refusal reasons to bbload0.log, but the previous run saved only stderr containing a temporary folder path and lost the contents on runner disposal. New CI captures ONLY local ephemeral synthetic shadnet.log and bbloadN.log before cleanup, redacting common credential patterns, to identify exact refusal reasons. 200-player test must remain gated on 4 active players.


## Real 4-peer refusal diagnosis, 2026-10-26
CI 40379442426 logged exact message 'another build: your game is another release (it says bbload)'. Even temporary CheckServerBuild=false did not disable the separate network protocol BuildRefusalOf. Official server protocol fingerprint is bb-build 1;version=dev;protocol=9;. Original bbload.cpp defaults its --build to bbload; original pinned loadtest/run_load.py uses args.extra.split() which breaks fingerprints with spaces. Added source-pinned test-only script (original git blob 96d9de56) that substitutes shlex.split and passes --build full synthetic dev/protocol9 fingerprint, without weakening any production build or server checks. Test outcome still pending.
