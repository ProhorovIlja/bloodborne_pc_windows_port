# V25 Opt-in transport ID binding for strict co-op/PvP rooms

Observed pinned code: ServerLink::Hub already carries link online_id and optionally
a SignIn(online_id,secret) callback; the co-op service blindly accepted separate
Hello.member and LobbyHello.member. Emulator BoardMemberOfOnlineId encodes the
transport ID to lowercase hexadecimal bytes, so identity equality can be tested
without changing protocol 7/8.

- With SH_STRICT_MEMBER_ID_BINDING=1, the co-op and lobby handshake reject
  claims for other member IDs. The network hub rejects **all** links if SignIn
  verification was not configured. The account secret is never logged here.
- Default OFF: old CLS/PS4/BBPort co-op behavior unchanged. **Not intended for
  production use without verification of SignIn credentials and two-PC tests.**
- Only binds envelope name to the name presented at the logged-in transport.
  It does not attest process memory, validate characters/inventory, prevent
  forged position/combat packets or guarantee the SignIn provider is secure.
- Strict PvP also needs a server-issued role/session token, negotiated protocol,
  privacy-filtered HUD streams and controlled matchmaking. V23 policy is dormant.
- No launcher UI toggle or server deployment in this release.

Tests: Python fail-closed source-anchored patch tests, C++20 identity tests.
GitHub Actions and full Qt server build need verification. Production Fornex
CLS server untouched.
