# Native port: release contract and research ledger

## Retail startup: first-load correction (V440)

On the private CUSA03173 image, disassembly of the ELF initializer shows the initial legacy cursor being read **before** the backward decrement. The initial slot is zero on disk but has an executable relative relocation. Independently walking both SCE relocation ranges found 18,444 distinct callbacks from the first load and 18,443 when starting one slot later. No callback address or game bytes are published. This is a static audit, not execution. The historical replay reports used the 18,443-entry reference; do not add one to their verified prefix or declare 1089 solved. Recover their exact inputs, compare recorded identities against the first-load order, and replay from its first constructor. Preserve the V434 rebuild gate and the V439 checks.

## Ship only a bring-your-own-copy toolchain

Public releases contain original project code/tools, permitted dependencies, synthetic tests and documentation. Users supply their own compatible Bloodborne dump; original executables/assets are private local setup inputs. Generate translated code and any derived native binary locally, outside Git. Runtime must pass with original executable unavailable: no PS4 ELF or EBOOT loading, JIT/interpreter fallback, PS4 firmware requirement or Sony services. Asset access and native executable loading are separate. Do not distribute retail bytes, derived game code, assets, keys, patches containing retail payloads, or private traces. Review rights and dependency obligations before distribution; this boundary does not guarantee immunity from claims.

## Acceptance gates

- Native Windows x64, Linux x64 and macOS arm64 first; test on real machines, not just CI. Reach startup, main, title, save/load, a playable map and full-game regression before calling it a port release.
- Fixed 60 Hz simulation with independent render cap/unlocked presentation. Verify physics, animation, sprint/stamina, hit windows, AI, scripts, online state and saves at multiple presentation rates and during stalls. Interpolate presentation, not authoritative game state. No claim that an emulator uncap patch proves this.
- Measure cold/warm launch, exit, memory and GPU budgets, input-to-present and p50/p95/p99 frame time; minimize startup work without deferring errors or compromising save flush. Test shader warmup, asset streaming, stalls, vertex cache corruption, device loss and recovery. Native backends first; add upscaling and latency controls only where measured and supported.
- Launcher: per-game profiles, settings validation, safe updates and rollback, diagnostics, controller and keyboard/mouse remapping, chord bindings, controller glyphs and optional dedicated jump. Keep advanced graphics, display, accessibility and frame pacing options discoverable.
- Online: offline remains usable, then LAN/direct/self-hosted and compatible public server modes. Measure RTT, jitter, packet loss, reconnect, state divergence and server CPU/bandwidth. Keep authoritative shared state, protect saves, and use reproducible loss/reorder tests. Zero latency and zero bugs are not verifiable promises.
- Keep vanilla as a baseline. Optional gameplay/QoL behind settings or profiles: remapping/jump, manual NG+, HUD and co-op toggles. Evaluate patches/mods by isolated change, compatibility and license; no blanket imports of other people's code or assets.

## References and intake

- bloodborne-native/bloodborne-recomp (https://github.com/bloodborne-native/bloodborne-recomp): AOT generation reference; keep the repository's pinned emitter until registry and ABI parity is verified.
- bloodborne-native/bloodborne-runtime (https://github.com/bloodborne-native/bloodborne-runtime): native Metal/Vulkan and service reference; runtime compatibility is not proof of an ELF-free launch.
- shadPS4 and patch ecosystem (https://github.com/shadps4-emu/shadPS4): timing, renderer and regression references. Compare 60 FPS/delta and uncapped behavior; do not treat patches as a native simulation contract.
- eFMann/shadPS4-Bloodborne-DLSS-FSR (https://github.com/eFMann/shadPS4-Bloodborne-DLSS-FSR): compare upscaler integration; benchmark native rendering separately.
- BBSC/Yharnam Together and private Bloodborne/DS3 research: references for session flow, asset formats and gameplay semantics. Never package DS3 files or make DS3 a runtime dependency.

For each useful upstream repository, fork, PR, issue, video or forum finding record the exact source/ref, license or unknown status, feature, regression risk, reproduction, decision and test result. Search broadly but do not claim an exhaustive index or copy sources without permission. Keep sanitized decisions in GitHub and the detailed private research index in Drive.
