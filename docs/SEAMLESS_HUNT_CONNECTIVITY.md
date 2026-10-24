# Seamless Hunt: native client connection diagnostics (phase 1)

This is the **first delivered native-client integration step**, not yet a multiplayer protocol bridge.

## What ships

- In the Windows launcher's **Party → Connection** section, press **Check Seamless Hunt**.
- It checks TCP connectivity to shadNet (31313) and its Web API (31315).
- It also sends a read-only HTTP `HEAD /ss.info` to the GameServer on port 20443.
- The GUI does this on a background thread and displays the result; checks are **manual only**.
- It never sends an account password, an authorization token, a party code, a save file, or gameplay frames.
- Command-line equivalent: `python scripts/seamless_hunt.py`. To test a separate staging host:
  `python scripts/seamless_hunt.py --host staging.example.org --json`.
- This is based on the Seamless Hunt source archive and production port inventory from 2026-10-22.

## What the results mean

"TCP reachable" only proves that a TCP socket opened. It does **not** prove successful account sign-in, session creation, NAT traversal, matchmaking, or interoperability between shadPS4 and this native port.

The GameServer check verifies that HTTP `HEAD /ss.info` returns `200` with a `text/plain` content type, as implemented in the supplied server source. It does not parse or return the server's `ss.info` body.

This does **not** change visy's direct P2P, party-code protocol, DHT rendezvous, UDP, member relay, existing saves, or gameplay behavior. It does not deploy or patch the user's production VPS.

## Next protocol milestone

Implement account-backed session discovery behind a **disabled-by-default** option, with a security review of the server's authentication endpoints and encrypted transport. The existing shadNet Web API uses authenticated PSN-style session routes; these are **not** a compatible replacement for the native port's BBP3 party-code or P2P protocol.

A future adapter must publish/resolve native party invites without disclosing join secrets, authenticate users securely, verify access on every transport route, and preserve legacy BBSC clients until a real cross-client protocol bridge exists. Do not assume switching the URL to Seamless Hunt makes native and shadPS4 sessions interoperable.

## Verification

`python -m unittest discover -s tests -p 'test_seamless_hunt.py' -v` runs offline using mock sockets, with no production network traffic.

The `native-client-checks.yml` GitHub Actions workflow runs this alongside existing party environment and save safety tests. Full C++/Windows compilation and two-PC gameplay testing are still required before calling a release production-ready.
