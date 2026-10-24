# Seamless Hunt Accounts V32: Public Realm, Private Realm and Legacy P2P

**Status: staged design plus limited WebAPI security fix. No live account portal or launcher sign-in is deployed.** This note does not change the CLS/Fornex production service.

## Why this is a new feature, not a built-in Yharnam Together login

In the pinned `lKaniel/bloodborne-server` server, `ClientSession::CmdCreate` and
`ClientSession::CmdLogin` are legacy internal account commands, and
`LinkServer::SignIn` authenticates a transport identity. Neither is
a finished site-registration-to-native-launcher login. The included
`website` is primarily a promotional and documentation website, not an
existing user-account frontend. The native Windows launcher presently
offers offline and direct party modes; it must not be forced into a
previously non-existent account system.

## Four operating modes

| Mode | Site account required? | Connection | If remote account host is down |
| --- | --- | --- | --- |
| Solo | No | Local game only | Works |
| Direct party / existing CLS-PS4 bridge | No | Host/peer or legacy compatible realm | Works where its own network still works |
| Public Realm (new) | **Yes** | A dedicated remotely hosted game backend; user needs no local server | Only public entry fails; game still starts solo |
| Private/Local Realm (new) | Server-configurable | The server owner chooses local/LAN or remote | Depends on selected private realm only |

The **launcher** may show server and account status, but cannot issue
a valid login locally. The **server** authenticates every online admission.
A user without a local server can join the public realm if it is reachable
and authorized. If a server is not reachable, the public mode fails closed;
the launcher must not fake a login or spin up an emulator.

## Browser registration and login, planned but NOT implemented

1. Use a **verified HTTPS website** with registration, unique player ID,
   email verification, password reset and optional passkeys/MFA.
2. "Sign in" launches the system browser. Implement Authorization Code
   with PKCE or a carefully implemented OAuth-style device flow; **never**
   ask the Tkinter launcher to receive or save the site password.
3. A token with narrow scope (`realm:join`), short TTL, issuer and audience
   checks is stored in Windows Credential Manager, not
   `launcher_settings.json`, game saves, telemetry or URLs.
4. Select public/private realm, fetch capability/protocol negotiation
   through HTTPS and request a **short-lived, single-use admission ticket**.
   Ticket binds account ID, selected realm, client nonce, protocol, short
   expiration, and server-issued challenge. Realm must verify replay
   protection and account bans **server-side** before opening game routing.
5. Revoke session and future tickets on logout, password reset or ban;
   revoke **active** links using existing Hub departure cleanup when
   enforcement is enabled after real-world interoperability testing.
6. Game server and website use separate credentials. Never reuse the
   current legacy plaintext UDP Hello password or existing WebAPI Bearer
   token as a long-lived public-realm admission credential.
7. SSL/TLS certificate verification is mandatory. Never "ignore cert
   errors." Do not embed signing secrets in the client.

### Illustrative API contract, not live endpoints

- `POST /v1/auth/device/start` -> ephemeral device code and browser verification URI.
- `POST /v1/auth/device/poll` -> pending/denied/expired/success; rate limited.
- `GET /v1/realms` -> signed/trusted metadata and compatible protocol versions.
- `POST /v1/realms/{realm}/ticket` -> one-use admission ticket for logged-in player.
- `POST /v1/auth/logout` -> session revocation.
- `GET /v1/accounts/me` -> identity/profile status, no password returned.

Endpoint names are requirements to implement and review; do **not**
put them in the shipping launcher until working server routes exist.

## ShadNet security hardening already staged

V32 patches the pinned `WebApiAuth::Authenticate` so a token from a
banned account is refused with the same invalid-token error used for a
revoked token. It also creates an index on `account(token)` even for
existing SQLite databases, avoiding O(n) account-table scans per bearer
request. This improves the current backend but does **not** make it a
public-facing OAuth identity provider; no auth endpoint is implemented.

The `account_modes.py` client UX policy tests distinguish
`solo`, `direct-party`, `legacy-cls`, `public-realm`, and
`private-realm`. Only the new public mode always requires both
website login and **server-confirmed** admission. The private owner may
opt out of accounts. UX mode selection is not a security boundary.

## Compatibility and release gate

- Existing PS4 / CLS / native direct party clients cannot be silently
  forced into the public account handshake. Cross-client federation
  requires a separately versioned compatible gateway and testing.
- Prove offline and direct games are unaffected.
- Create and deploy actual HTTPS identity service and site page; verify
  CSRF/state, PKCE, OAuth response validation, token storage, rate limits,
  reset flows, phishing protections and privacy controls.
- Require signed server-side game tickets and test replay, expiry,
  stolen tokens, incorrect realm/ID, banned accounts, DoS and reconnect.
- Test one account on Windows native port, account switch, expiry, bad
  connectivity, full game restart, PS4 legacy peers and cross-region.
- Pass source CI, real Qt server integration builds, Windows launcher
  and game startup tests before proposing production settings.

**No currently deployed domain, account registration page or hosted
game server is claimed by this document.**
