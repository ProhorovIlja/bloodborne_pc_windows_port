# V439/V440: New BBHost network candidates, source-traced 2026-11-07

## Selected code: independent API17 candidate, NOT a release

- Baseline production research: **BBHost v0.2.24** `b0098e04b889e2e70b4af84be1ce809d7af3ff95`, public **plugin API16**; our pinned original YT v1.4.0 five-member protocol/Qt tests are unchanged and remain separately green.
- [BBHost PR #217](https://github.com/droogie/bbhost/pull/217), head `271f68ef8811b873c7e0cc31f98a92f8deb7e999`, 16 commits ahead of v0.2.26 `bdc5cdf8be5f37188da9c2368e92be444fdc04cb`, changes **multiplayer signaling, Matching2 lifecycle, transport identity, events, plugin API17 and diagnostics**. Its author warns **client and server must both update**; not a drop-in replacement for our live shadNet/BBSC or original YT server.
- V439 extends `apply_bbhost_plugin_to_actual_host_v3.py` with **explicit opt-in** `--allow-pr217-network-candidate`; exactly pins candidate CMake and API17 Git blobs and original `np_signaling.cpp`, `np_matching2.cpp`, `net.cpp` and `net_p2p.h`. The existing v0.2.24/v0.2.25 path explicitly rejects this flag and remains unchanged.
- Separate CI `bbhost-pr217-network-api17-candidate` compiles **our real Linux .so** against actual PR217 API17 and vendors original YT Noise-NK/SHLK4 code, runs the original BBHost plugin `dlopen` fixture, and proves the **source gate refuses PR217 without opt-in**. This demonstrates plugin-level **ABI compatibility**, not runtime signaling correctness, NAT interoperability, engine hooks, guest NetSync or five-game online.

## Security finding and V440 candidate gate

PR217's unencrypted UDP signaling datagrams use exact **46 bytes**: `kSignalMagic = FE 62 62 73`, kind, reason, 16-byte source OnlineID, 16-byte target OnlineID and 8-byte nonce. In `src/hle/np_signaling.cpp` (Git blob `4668783f279c9e6c65e48b3c31c956c29056bf61`), `send_locked` sets the *target*, but `hle_np_signaling_control` previously parsed only `from` and immediately processed an incoming frame, potentially updating the source address and transport state. This is a **recipient-validation gap**, not proof of an attack on the user or a working exploit.

- `shyt_bbhost_signal_target_v440.h` is a bounded, pure, no-network 46-byte validation gate: checks magic, known message kind, exact recipient OnlineID, nonempty canonical NP identifiers and no trailing nonzero bytes after NUL. Its test covers all eight original control kinds, misaddressed packet, mismatched casing, truncated and overlong packets, corrupt padding, and invalid IDs.
- `apply_bbhost_signaling_guard_v440.py` makes an **isolated, exact-source-pinned** overlay of only PR217's `np_signaling.cpp`, injecting the recipient gate **before any transport-state processing**. The script does not change production, any original pinned releases or the actual GitHub upstream PR. It is a security-review candidate, not accepted upstream code. The new code's compiler/unit test checks the source-level gate, but does **not** compile or execute PR217's full original signaling subsystem.
- **Critical:** A packet with a *forged but well-formed sender* still passes this V440 check. **Neither V440 nor original PR217's unkeyed control packet authenticates a sender, endpoint or team member.** Do not enable direct-game traffic or host-side signaling decisions without cryptographically/server-bound peer identity and stable room/session/owner permissions. NAT rebinding also needs explicit revalidation.

## Independent parallel candidate: features, performance, and auth

- [BBHost PR #218](https://github.com/droogie/bbhost/pull/218), head `57ecf8327b9201f801910934dde48f2dd592a714`, 20 commits ahead of the same v0.2.26 base; **branches diverge from PR217 (16 behind/20 ahead)** and cannot simply be merged as one release.
- PR218 includes `src/net/sign_in_check.h` and real `tests/sign_in_check_test.cpp`: distinguishes actual server-issued `ResKind=1` refusals from **429/500/network failures/unknown 404**, preventing failed lookups from being treated as explicit revocations. Source-pinned in a *separate* CI test of the actual PR218 parser.
- The PR's author reports real five-game tests of **Full Phantom HP** (SpEffectParam visitor rows; per-visitor setting) and **Auto-Replenish Items** (EquipParamGoods). Treat these as credible upstream test reports, **not** tests of our SHYT integration. These changes, diagnostics and FPS improvements need game-version, source-license, options UI, save safety, and performance regression reviews before selective adoption.
- Recent YT upstream [#540](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/540) addresses hosted flood-protection banning an address during a multiplayer session; [#539](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/539) addresses Windows trust-store sign-in. Both warrant separate production-owner review. **No Fornex changes here.**
- CLS gameplay candidates (DBNO/revive, boss death/resync, guest visibility) and BBHost rendering candidates remain monitored separately; the separate fully native EBOOT-free PC port must not be mislabeled as a BBHost compatibility build.

## Real promotion gates

1. **Source/ABI:** V439 candidate plugin build and V440 focused wire/source tests pass independently of v0.2.24 baseline; no silent upgrade. Then compile and test **actual PR217 signaling subsystem**, not only its plugin API.
2. **Authorization:** server-signed OnlineID -> party member/endpoint -> source and receiver in-game identity; refuse unauthorized transport before handshake, rebind only after server proof, drop stale epoch/room/owner/match changes. No cleartext signal should grant a game route.
3. **Routing:** preserve original YT `GameFrame` actor/map/owner/invasion rules, reliable sequence tombstones and room lifecycle; verify direct P2P/relay transition with authentic client/server crypto, not only NAT probe success.
4. **Gameplay:** real two-through-five PC test matrix, 4+1/3+2 invasions, save and death/DBNO consistency, disconnects, NAT cases and per-route bandwidth/latency/CPU/1%-low. Only then consider deployment.

No game EBOOTs, assets, secrets or private identities in any repository/CI.
