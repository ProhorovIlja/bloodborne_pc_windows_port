# V28 Pre-Database UDP Hello Admission Guard

Pinned upstream: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`.

**Confirmed attack surface:** `Hub::OnHello` could call a `SignIn` callback for an unlimited stream of new account names before any cheap per-source/global admission test. The actual shadNet `LinkServer::SignIn` callback checks its fast cached secret hash for known accounts, but performs database credential checks and/or account creation for a new ID. This is expensive under sustained bogus or high-volume account attempts.

V28 implements a fixed-memory four-way set-associative IPv4 admission guard and two O(1) integer token buckets, executed in `Hub::OnHello` BEFORE the DB-backed `sign_in` callback. No per-connection allocation, background job, persistent ban list or filesystem access.

Provisional values: 8 Hello attempts per source IP initially, replenishing 2/s; 24 attempts globally initially, replenishing 6/s. Same-IP NAT clients share a budget. A fixed 8192-slot table uses 30 s idle leases; when no slots are available in a bucket, admission fails closed. Rejections are silent because older games retry the Hello, whereas an explicit welcome refusal may terminate the login flow.

**OFF by default:** enable in an isolated staging server by setting `SH_LOGIN_ADMISSION=1` before server startup. The production Fornex/CLS service is unchanged; don't enable until Qt integration, reconnect/login spikes, party-size, busy-server and legacy PS4 compatibility tests confirm suitable thresholds.

Tests: portable C++20 `Gate` tests compiled locally under GCC14 with strict warnings and UndefinedBehaviorSanitizer, 5 Python fail-closed transformer tests. Integration additionally injects a Qt Hub test into the existing pinned `server/tests/test_server_link.cpp`: forty attempts from one IPv4 should invoke auth just eight times, then one after 500 ms. **Qt executable not yet built**.

This is a work-limiting control, not account authentication and not full DDoS protection. A large botnet can still consume the global allowance and induce availability loss. Authentication and account creation policy, replay protection, IP allowlists and firewall rate limits need a separate, measured design. `m_signedIn` also caches signed-in hashes across sessions and warrants a dedicated eviction review.

No production services modified.
