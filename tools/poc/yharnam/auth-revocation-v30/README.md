# V30: Immediate credential revocation on cached game login

Confirmed pinned source defect: LinkServer::SignIn had a persistent m_signedIn
cache keyed by player ID holding SHA-256(secret). A cache hit compared ONLY
that in-memory hash and skipped the database. Thus after an account was banned,
deleted or had its DB password changed, the cached old password could remain
accepted until eviction or server restart. V29 limited cache size but did not
fix this authorization flaw.

V30 adds Database::CurrentCredentialStatus, an indexed read-only SQLite SELECT
of the current database salted-password hash and banned bit. Every cache hit
checks this live status before it may be accepted. The 100k-round password KDF
is NOT rerun on ordinary cache hits. Deleted/banned/DB-inaccessible accounts are
rejected immediately and cache entries are dropped. Password rotation drops
the cache and verifies the proposed new password through the regular database
path; the old secret fails. Freshly verified banned accounts are also denied.

A successful cache entry now contains both SHA-256(client secret) and a snapshot
of the DB salted credential hash. The V29 2048-entry cap remains.

Source transforms are deliberately strict against the pinned commit. Standalone
C++20 policy and Python transform tests are provided. A real Qt/SQLite account
regression must pass via the composed Linux server build before production use.
No live CLS/Fornex changes, and no promise that the entire game client builds.

This corrects *new authentication decisions*. To expel an already connected,
active banned client without waiting for its next Hello, enforce status checks
at the active network session or add server-initiated disconnect on ban. That is
not yet implemented. The UDP login secret is not encrypted by itself; ensure
network confidentiality with an appropriate secure transport.
