# Bloodborne: Seamless Hunt — TWO EQUAL MISSIONS (canonical charter)
Updated 2026-11-01. Read this first before any development or continuation.
This is the user's explicit scope, not a claim that features already work.

## Mission A: The best *playable* Bloodborne PC experience, one polished launcher
Deliver one integrated product: game client/runtime, launcher/installer/updater,
dedicated server and hybrid online, performance, graphics, input, stability,
gameplay fixes, co-op/PvP, saves, mod profiles, patches, features and settings.

Do NOT limit this work to the current Yharnam Together / BBPort runtime. Treat
**BBHost as a serious candidate primary runtime** if independently reproducible
measurements and compatibility gates show it is better. Other candidates and
sources: Yharnam Together (lKaniel), CLS branches/tests, BBPort, supermedo,
Lantern Engine/Awaken, shadPS4, deadinside/AwesomeObserver, visy,
bloodborne-native, Souls-family and Dark Souls III research, relevant forks,
branches, PRs, mods, community websites and documented engine behavior.
Research by bounded, pinned-source reads, not speculative copy-paste.
Reuse existing correct features instead of implementing duplicates.

Must cover, subject to compatibility and validation:
- Smooth PC runtime/rendering; shader cache, GPU/CPU utilization, frametimes,
  input, audio, loading, GPU/driver differences, frame pacing, safe presets;
- one integrated launcher with installation/update/repair, backups/restore,
  profiles, configuration, safe mod/patch conflict diagnostics, accessibility,
  keybinds, graphics/performance presets, diagnostics and rollback;
- stable hosted server and private/local servers; discovery, friends/invites,
  joining in-progress worlds, matchmaking/filters, public/private parties,
  five-player team support with correct HUD/world entities, invasions/duels,
  host-controlled options, late joins, map transitions, DBNO and save safety;
- authenticated **direct UDP P2P for eligible high-volume gameplay**, STUN /
  NAT traversal / hole punching, and measured safe relay fallback where direct
  connectivity is unavailable. Server remains authoritative where necessary
  for sessions, accounts, permissions and consistency. Do not turn the VPS into
  a forced high-rate gameplay relay for every connected player.
- test real reported bugs separately (Hunter's Dream visible name/HP with
  invisible body, ?ActionEventInfo?, connecting to an active host, copied-save
  duplicate rewards, map transitions). Do not claim resolved from CI alone.
- optional gameplay features/patches including manual NG+, respec, lamps,
  jump bindings, cosmetic/optimization mods and other compatible improvements;
  never auto-enable all mods, publish proprietary assets or risk save corruption.

Current starting point (verify before asserting as latest):
- Our GitHub playable Draft PR #85; baseline official YT v1.3.1. Upstream
  five-player PR #484 and test PR #486 were Draft when last checked.
- Mod preflight V232/V234 and capacity gate V233 are **preparatory tools**,
  not an installed finished launcher or proven VPS performance gain.
- Direct P2P policy V231 is not a deployed encrypted P2P transport.
- Do not modify production Fornex without explicit authorized release/deploy
  preparation and verified rollback.

### BBHost vs BBPort/Lantern/YT: evidence-first decision
BBHost documentation describes native execution of original guest x86-64 code,
native replacements for PS4 interfaces, P2P UDP + STUN and fallback. YT v1.3.1
describes server-relayed game UDP; Lantern Engine documents performance
improvements to a bbport/shadPS4-derived implementation. None of those claims
alone proves BBHost gives higher FPS, seamless-team compatibility or lower
real-world VPS load.

**Do not prematurely lock the architecture.** Test four candidate paths:
1. Preserve playable YT v1.3.1, add verified P2P and optimize its components.
2. Port seamless-team/client protocol to BBHost when legal/technically feasible.
3. Adapt proven BBHost/Lantern renderer/runtime/network features into a
   compatible YT branch where source-level portability permits.
4. Prefer a hybrid only if it beats simpler paths in measured reliability,
   feature completeness and maintainability, not because of its label.

Compare same retail game version/patch, exact build/commit, CPU/GPU/driver,
resolution/scene/mod profile and 2- vs 5-client session conditions. Record
p50/p95/p99 frame times, avg/1% lows, stutters, crashes, memory, shader
compilation/warm-up, server CPU and memory, bytes/s and packets/s, p95/p99
network RTT, packet loss, join time, session recovery, NAT success and relay
fallback. Separate test lab and production. Reject a proposed switch if
seamless gameplay breaks, players disappear, saves regress, privileges leak,
or the online load budget is worse, regardless of raw FPS.

Do not assume YT and BBHost network protocols are wire-compatible.
No cross-runtime online or perfect 5-player support until actual tests prove it.
Respect GPL and additional author NOTICE terms before code combination.

## Mission B: Truly standalone native Bloodborne Windows PC port
This is an INDEPENDENT project, not the rebranding of BBPort/BBHost,
a PS4 ELF translation/hosting layer, or a launcher invoking eboot.bin.

**Final acceptance contract:** native Windows Bloodborne.exe / runtime,
game logic built into native Windows machine code or equivalent authored
native source, native Windows ABI/platform components, PC graphics/audio/
input/files/saves/network, complete game startup and play from title through
all areas/bosses, multiplayer support as separately validated, and **no
requirement to load or execute original eboot.bin / PS4 ELF at runtime**.
Original user-owned Bloodborne 1.09 (CUSA03173, decrypted ELF), assets,
Dark Souls III PC version and public reverse-engineering research are valid
PRIVATE analysis/build-time input, not redistributable game code/data.
No public uploads of proprietary binaries or private assets.

Continue Draft PR #84 rather than restarting. Prior private AOT pass reportedly
generated 384 C modules for 241,031 registered of 241,821 indexed functions;
Windows COFF compilation, runtime math ABI dispatch and memory management
are partial proofs only. They are NOT a fully native playable executable.
Key gates: compiled complete actual AOT, resolve runtime/interpreter fallback,
correct ABI and import implementations, native memory ownership and init,
Windows graphics/audio/input/assets/saves, determinism/correctness, launch,
level traversal, real gameplay, comprehensive regression/performance tests.
Dark Souls III may inform formats/architecture, not guarantee drop-in code.

## Cross-project rule
The two tracks may share findings, tests, mod/asset format research, tools and
native PC subsystems, but **success/progress in one does not complete the other**.
Avoid endless isolated demos: prioritize blockers to usable gameplay in A and
real native game startup in B. No duplicate work already completed upstream;
check recent code/PRs/forks for relevant improvements before implementation,
and verify their dates, implementation and limitations.

## Materials and durable state
- gungrain@gmail.com Drive: Bloodborne — Seamless Hunt — HANDOFF
  (00-START-HERE, 01-HISTORY-MD, 05-TESTS-LOGS, source archives).
- Private game resources: CUSA03173, CUSA03173-mods, user mods/XML, Dark Souls III.
- GitHub: ProhorovIlja/bloodborne_pc_windows_port, Draft PR #85 and #84.
- Existing Drive note: "Bloodborne — Best-of Engineering Checkpoint —
  2026-11-01.md" for evidence, constraints and already implemented preflight.

## Research and ChatGPT "Error in input stream" discipline
Read docs/CHATGPT_SAFE_REMOTE_RESEARCH.md. Never fetch complete CI logs, huge
diffs, entire source trees or bulk game binary dumps into chat; use narrowly
bounded chunks (<=60 lines/source read), at most two remote calls per
research batch and truncate tool output summaries to ~1500 characters.
Analyze large data locally and keep only concise metrics, hashes and
reproducible small findings. Persist checkpoints, commit+hash manifests and
status so a new chat resumes rather than redoing jobs. Keep game files
private. A GitHub change cannot fix ChatGPT infrastructure transport errors;
this workflow reduces exposure but does not promise zero platform failures.

## Public technical references (claims must be re-verified by source and commit)
- https://github.com/droogie/bbhost/blob/master/README.md
- https://github.com/droogie/bbhost/blob/master/docs/online.md
- https://github.com/lKaniel/bloodborne-server
- https://github.com/Awakenchan/LanternEngine/blob/main/engine/README.md
- https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/84
- https://github.com/ProhorovIlja/bloodborne_pc_windows_port/pull/85
