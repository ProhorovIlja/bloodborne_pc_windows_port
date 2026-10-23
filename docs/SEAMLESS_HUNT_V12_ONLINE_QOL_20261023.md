# Seamless Hunt V12: safer in-game online UX and quality filters

Development checkpoint: 2026-10-23. Source-level changes, NOT a Windows game build and NOT deployed.

## Code landed

- The existing unified compiler input tools/poc/yharnam/unified-v9/compose_sources.py now applies the V11 optional rejoin patch AFTER V5 DBNO, V3 UI Scale and V10 guarded native P2P. It brings forward the same in-game Team menu and adds last_session_policy.hpp, with strict source anchors.
- tools/poc/yharnam/last-session-v11/patch_native_resume.py now lives in GitHub, rather than only inside a conversation ZIP. It introduces Off / Ask / Auto for title-screen previous-hunt rejoin, with server team membership checks, exact character slot, world/party, protocol and expiry. Existing mid-game link recovery is not gated by this preference.
- tools/poc/yharnam/quality-v12/quality_filters.hpp: native C++20 candidates for shared lobby browser and Quick Play presets: Balanced (120 ms), Low Latency (60 ms), Friends and Unrestricted. All filters enforce public/no-password, exact compatible game build, capacity and host invasion opt-in. Strict ping filters reject stale, unverified or missing peer measurements. The room quality is the WORST measured RTT across peers; mixed P2P/relay is represented as Mixed, not as pure Direct.
- Existing tools/poc/yharnam/ingame-online/ping_policy.hpp fixed: DirectOnly NEVER accepts relay fallback or unknown direct RTT, even when no explicit millisecond cap exists. Test updated.
- tools/poc/yharnam/unified-v9/test_compose.py updated to test combined V11 menu/source and six generated support headers. The default-branch GitHub Actions source-gate now includes C++ native V11 and V12 tests and asserts V11 exists inside assembled game source.

Local checks: archived V11 native CTest 1/1; archived V11 Python patcher 3/3; V12 V11-after-V3/V5 composition Python 2/2; V12 native C++ quality filter 1/1. These 7 checks pass locally. New GitHub-composer changes and remote CI still await a completed GitHub Actions run. No full overlay compilation/gameplay test or server authorization was performed.

## Important fixes and caveats

1. Don't let Friends preset act like Unrestricted: require a server-confirmed friend_of_host field. Client-side filter is cosmetic, server is authoritative.
2. Don't present a relay RTT as a successful DirectOnly candidate. Don't show VPS RTT as peer ping. Unknown/unmeasured routes must stay clearly unknown.
3. Protect password and private rooms from public search and random invasions; server must check identity and authorization again on reservation and join.
4. Last session: do not autojoin a different team after the old room expires. The present title rule validates account/team/world/slot/protocol, but needs a server-generated per-hunt epoch ID before publicly enabling Auto to distinguish a restarted hunt within the SAME surviving team.
5. Current actual server does NOT yet issue P2P candidates/keys or revoke per-map/owner grants; high-rate channel 0x06 still relays. V10 guard correctly blocks unsafe direct bypass. No CPU savings claimed.

## Next safe enhancements, prioritized

High priority: in-game Network tab showing Direct/Relay/Mixed/unknown, RTT (worst member), packet loss and jitter; precise reasons when Quick Play rejects a room (full, stale ping, version, privacy, DBNO, PvP disabled). Atomic reservation, never join after client-only filtering.
High priority: per-save online presets persisted in BBPort user directory, user-visible revert to defaults; private/password room policy and friend-only joining; automatic no-service/retry HUD without spamming.
High priority: compatibility page: game build/region/patch, native runtime build/protocol, installed mods/patches fingerprint, save format; reject mismatches before connecting while never uploading private save content.
Medium: accessibility sliders for HUD UI scale and opacity, high-contrast role outlines, controller focus/hold-to-confirm for destructive settings. Camera/graphics and shader cache tuning only with benchmarks and rollback.
Medium: game QoL optional host-authoritative revive, team HP/cards, travel synchronization, ready checks, reconnection, per-room invasion rule and non-duplicating loot policy. Avoid rebalancing enemy damage/health by default.
Nice-to-have: favorites, recently played hunters, server-side blocked players, invites, status indicators, short-lived manual reconnect invitation and named presets.

## Release gates

Real Windows native binary plus matched Qt Linux server with protocol 8; actual signed peer identity and NAT traversal; per-room authoritative rules and cancellation; two-client live gameplay; crash/reconnect/death/invasions; Windows update and server rollback; 200-player load measurements. No install to production CLS/Fornex.

GitHub CI manual link: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v9-source-gate.yml
Google Drive project handoff: https://drive.google.com/drive/folders/1_Yjz9ysS5mhL0mXUEoRqz0u3bjK6sIxM