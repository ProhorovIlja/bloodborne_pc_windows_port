# V86: game-owned full-identity SHG2 inbox

This is an opt-in developer-only integration into the **original Yharnam Together native Windows game's P2PTransport**, not a separate launcher, another multiplayer protocol, or a new daemon.

## Implemented

The pinned source overlay `patch_native_shg2_owner_v86.py` runs after the existing V82/V83 transformations within `unified-v9/compose_sources.py`. It fails closed if any expected source anchor changes or it is applied twice.

- The original native game `P2PTransport` now owns a **second** `NativeSealedGrantInboxV84`, independently of its previous V82 SHG1 inbox.
- The V84 inbox and V85 native mTLS client are compiled only with the **preexisting** `SHYT_ENABLE_TEST_LOCAL_MTLS` CMake opt-in flag (default OFF); no new runtime flag or automatic connection is introduced.
- The existing native transport `native_grant_mutex` guards the one synchronous development call `TryLocalShg2OfferForTest`. The caller must provide authenticated full-identity current-game state, a monotonic TLS connection serial, a trusted refresh callback and a loopback-only X.509 TLS configuration. This patch does **not** solve secure identity extraction from the real game's online session and does not introduce any caller that could spoof game state.
- On existing transport socket shutdown and on account/server relink, both old SHG1 and new SHG2 pending secrets are revoked within the original grant lock. Pending grants are never permitted to call `Arm()`, `SendFrame()` or any Direct UDP route.
- Default shipping build remains inert. Live server/relay paths remain untouched.

## Tests and remaining work

`test_patch_native_shg2_owner_v86.py` checks both native lifetime invalidations, the dev-only opt-in guard, no game sender/receiver hooks, double application and pinned source drift. Native game client-server source provenance is checked separately. These are source-only tests; there has not yet been a full Windows executable compilation with `SHYT_ENABLE_TEST_LOCAL_MTLS=ON` or a playable two-PC session.

**Next:** obtain the *original game's verified online_id, peer selection and world epoch* from authentic native session state; tie it to the Qt full SHA256 issuer and authenticated certificate pin lifecycle. After that, use the existing game's UDP socket for authenticated NAT probes and AAD-bound encrypted datagrams, prove reliable GameLink ACK/sequence migration and fallback. No public Direct use until two machines and measured server savings prove safe.
