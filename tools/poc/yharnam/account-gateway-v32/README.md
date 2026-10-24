# V32 staged account gateway: compatibility-first

This is **not** a deployed website, credential service, or login form. It
distinguishes the existing *internal shadNet game-ID sign-in* from a proposed
browser-launched account login for a future dedicated public realm.

Confirmed pinned-source flaw: WebApiAuth::Authenticate previously resolved
Bearer tokens by token only and did not check the banned flag. An account
banned from the game could still use its existing WebAPI token. The V32
transform adds banned=0 to the token lookup and an index in Database::Migrate
for both new and existing SQLite DBs. Tokens retain the same invalid-token
error on ban or revocation; the game protocol and legacy PS4 behavior stay
unchanged. Token rotation/expiration and secure session transport remain
unimplemented; this hardening alone is not a safe web-login system.

Pure launcher policy `account_modes.py` defines Solo, Direct Party, Legacy CLS,
Public Realm and Private Realm. The public mode must see **all**: a reachable
remote realm, a compatible native client, an authenticated browser account and
a server-confirmed admission ticket. A local server is not required.
Private servers may choose their own account requirement. P2P and offline
never depend on an external website.

Future secure flow (no invented deployed endpoints):
1. Player clicks **Create account** in launcher; verified HTTPS portal opens.
2. Login in the system browser using device-code or authorization-code+PKCE.
   The native launcher never receives the password.
3. Client receives a short-lived scoped access token (Windows Credential
   Manager) and requests a **one-time** game admission ticket for the chosen
   realm. Ticket is bound to account, realm, client nonce/version and short TTL.
4. Game connects. **The authoritative realm**, not the launcher, verifies
   ticket signature, expiry, one-time use, banned status and protocol. HTTPS
   transport protects the browser token. UDP game hello carries only a
   suitable scoped proof, not a reusable account password.
5. Logout/revoke invalidates future admissions; bans remove active sessions.
   Existing CLS/PS4 clients use a separate legacy bridge, never a silent
   universal requirement that would break the installed ecosystem.

No hosted account portal, OAuth endpoints, token store or verified game ticket
issuer exists as part of V32. No production Fornex/CLS modifications.
