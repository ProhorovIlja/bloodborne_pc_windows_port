# V29: bounded RPC buffering and signed-in credential cache

Pinned source: lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15.

Verified source defects in server/src/link_server.cpp:
1. Incoming RPC data was appended to RpcEnd::pending without a bound while
   the local TCP backend was disconnected or connecting. Connected socket
   writes could also accumulate without checking bytesToWrite.
2. The signed-in SHA-256 credential cache never removed entries when new
   users appeared. This could grow in a long-running public server.

V29 checks the total buffered TCP/RPC bytes before copying into QByteArray.
Cap is 2 MiB per RPC tunnel. An oversized stream is marked blocked,
its socket is closed, and its tunnel is notified; subsequent data is ignored
until the next *Opened* event. It checks both pre-connect pending and connected
Qt bytesToWrite. A successful new login evicts one cached credential after the
cache reaches 2048 entries; evicted users are reverified through the normal
database path next time they sign in. The actual credentials DB is untouched.

No blocking IO, new background threads, bans or protocol messages. These
limits are initial values to tune with the full Qt server integration tests,
large friends/score RPC requests and reconnections.

The standalone C++20 policy and Python source transformation tests validate
the bounds and immutable source anchors. Full Qt binary testing and end-to-end
legacy client interoperability are still required. Production Fornex/CLS
not modified.
