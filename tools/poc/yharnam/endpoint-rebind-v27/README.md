# V27 Same-endpoint identity switch: stale virtual address fix

Pinned upstream: lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15.
Observed in server/src/server_link.cpp Hub::OnHello: when an existing
network endpoint switches to a DIFFERENT online_id, the code replaces
link.virtual_endpoint but doesn't call Unlink on the previous one. This
leaves by_virtual[old_virtual] and possibly in-flight packet pair state.

V27 detects only identity changes, not same-account reconnects:
- tell old party members it departed BEFORE removing the old identity;
- Unlink(old endpoint) clears old by_virtual route and packet pairs;
- result.gone reports it to the co-op service so old world membership can
  be forgotten;
- then continue normal new account link handling.

Includes isolated C++20 identity policy test, Python source-transform
tests and fail-closed source anchoring. This isn't proof of a Qt hub
integration build: it needs actual two-account/reconnection/host-migration
tests, especially when transport SignIn is enabled.

Does not modify live Fornex/CLS server. No automatic bans or extra threads.


**Additional integration regression:** V27 now patches the pinned `server/tests/test_server_link.cpp` test executable to run `ChangedAccountOnSameEndpoint()`, exercising an old virtual route that must be dropped and a newly registered virtual route that must pass. This Qt test was authored and anchored against the pinned source but **has not actually run** without a full Qt server build. The compositor also includes `server_link.h` and `link_server.cpp` changes, removing stale matchmaking `udpExt` records when an account changes on the same socket.
