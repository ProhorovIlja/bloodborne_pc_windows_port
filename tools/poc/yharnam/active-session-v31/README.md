# V31: Active revocation and stale matchmaking cleanup

Staged against pinned `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, after V27–V30. Source-only; no live Fornex/CLS changes.

The observed `Hub::Tick` expires inactive members using `result.gone`, but (unlike same-socket account switches patched in V27) didn't append their online ID to `result.retired_online_ids`. Matchmaking's `udpExt` virtual endpoint could remain stale. V31 always retires these entries on actual link removal.

Active ban/deletion/password-hash change checks are opt-in via `SH_ACTIVE_ACCOUNT_REVOCATION=1` for a staging server. At most eight cheap indexed SQLite lookups run per `Hub::Tick` (500ms), each linked player checked no more frequently than once per ~15s; revoked users travel through ordinary `Unlink`, Gone, party-world Forget and RpcEnd cleanup. No per-frame database checks, no new thread, no background banning task. Normal co-op and old clients remain unchanged when disabled.

The signed-in credential snapshot is held in V30's bounded 2048-account cache. If a cache entry has been evicted while the game remains online, V31 still detects deletion and bans, but **may not immediately detect password rotation** until another authenticated login: future design should store a per-active-link credential epoch or use explicit DB invalidation events. That limitation does not affect newly authenticated clients, which V30 verifies.

Isolated C++20 strict-warning and UBSan policy test and five Python source drift tests passed locally. Qt server integration test is included but **not executed**. Do not claim production-tested anti-cheat or deploy without real client compatibility and performance tests.
