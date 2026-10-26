# Experimental Yharnam Together 1.3.0 authentication cache migration

Pinned public original: 0645740a33ae21c56df3b4a0d9777086dbca6053 in lKaniel/bloodborne-server.
This is isolated C++ staging source, NOT deployed and NOT the current Bloodborne native client.

## Why

Latest LinkServer caches SHA256(secret) per ID. On a cache hit the original implementation accepts the old secret without checking whether its SQLite account was deleted, banned or had its salted password hash rotated. It also leaves m_signedIn unbounded in the reviewed source.

## Changes

The five source-file overrides under overrides/server/ implement a read-only, indexed SQLite credential-stamp lookup; recheck every cached Hello; reject deleted/banned/rotated/unreadable records; stamp both unhosted and hosted authenticated logins; verify that the async hosted worker's actual salted hash is STILL current on the Qt event thread; keep the cache <=2048 entries; and add a real Qt/SQLite test to existing test_accounts.cpp. No gameplay networking, account DB schema, P2P policy or live traffic changed.

## Applying only to a FRESH throwaway checkout

Use a fresh clone checked out at exactly 0645740a33ae21c56df3b4a0d9777086dbca6053, with no uncommitted changes. The staged overrides correspond to that exact pin. Validate original Git blob IDs before copying. Work only in an isolated test clone; do not copy these into the current 77e3507 client, which has a different source/API. Build the server with Qt6 and run its test_accounts plus link-server integration tests.

## Required before integration into full client

1. Compile genuine Qt6 shadNet C++; execute all upstream tests and test_accounts, inspect Qt warnings.
2. Add hosted/unhosted live-DB integration tests: password change while running, deletion, ban/unban, wrong cached password, right NEW password, worker-to-main callback race, 2048 unique IDs and admission limits.
3. Check automatic account registration policy before interpreting post-deletion reconnects, and verify region tickets/redirects.
4. Verify clean migration, protocol handshake compatibility, 2-player end-to-end and staging load/soak before PR integration.
5. No Fornex, CLS Friends, master, real accounts/saves or production firewall modification.

Original source-file Git blobs (verified via connected GitHub at this pin):
- server/src/database.h: 01f729832f96291d7b8e93401a27a07d4741efc4
- server/src/database.cpp: 9e9d52eadb69810a5c5bcf8389deae07cc831381
- server/src/link_server.h: 4530df9be35e161cd4e4fd56fe1f1696bb8b407b
- server/src/link_server.cpp: b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8
- server/tests/test_accounts.cpp: f22ab39b1e1c973573ca1ccf8e6dee06b0283d06

This staging source is not yet compiled and contains no claim of executable/game-ready code.
