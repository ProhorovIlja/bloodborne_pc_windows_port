# Seamless Hunt: Network Doctor (developer preview)

The single native-client fork contains an optional **Network doctor** button in **Party → Connection**. It is a real diagnostic, not yet matchmaking or an account login.

## What it checks

1. TCP connect to `play.seamlesshunt.com:31313` (shadNet) and `:31315` (Web API); neither transmits credentials.
2. `HEAD /ss.info` against GameServer `:20443` (expected `200 text/plain`, read-only).
3. RFC 5389 UDP STUN Binding Request against **the player's configured STUN server** (by default, `stun.l.google.com:19302`). It validates STUN cookie, transaction ID, attribute length, and mapped IPv4/IPv6 endpoint. It never logs the public IP.
4. IPv6 OS route availability by using `connect()` on a UDP socket, without sending a packet.

All checks are initiated manually and done in a background thread. The regular visy direct P2P networking, DHT, password protection, saves and game files are unchanged.

**Privacy:** the STUN server necessarily sees the computer's external IP/UDP source port. Don't run if you do not consent; set STUN to `off` to skip UDP. The source IP is not written to the launcher log. No game passwords, identity tokens or BBP3 party codes are sent.

**Interpretation:** working TCP and STUN do not establish that NAT punching works end-to-end. The IPv6 check only confirms a configured route. In particular it does not measure relay selection, packet loss or latency between two hunters. The definitive network validation remains a two-PC Internet host/join test using the *same current native build*.

## Site link

**Account website** opens `https://install.seamlesshunt.com` in the default browser. It does not transmit credentials to the launcher. Signing in directly to this native client is a separate later milestone requiring a verified HTTPS auth contract with the current site, encrypted token storage and a real session API.

## Development

Run locally, with no game installation:

```sh
python scripts/seamless_hunt.py
python scripts/seamless_hunt_network.py --stun off
python scripts/seamless_hunt_network.py --stun stun.l.google.com:19302
python -m unittest discover -s tests -p 'test_seamless_hunt.py' -v
python -m unittest discover -s tests -p 'test_seamless_hunt_network.py' -v
```

Tests use fake sockets, never a live production network. They run under GitHub Actions on **Ubuntu and Windows**.

## Building the Windows native runtime

The `Native Windows engine build` workflow is a separate developer CI job under `.github/workflows/native-windows-build.yml`. It initializes the original git submodules and uses MSYS2 CLANG64. Because MSYS2 doesn't package magic_enum/miniz, `tools/setup_windows_deps.sh` pins both to audited commits already used by Supermedo; the CMake Windows setup compiles miniz locally. Build result, if successful, is a **developer-only archive with binaries** from the GitHub Actions artifacts, not a game-ready distribution and not proof of in-game play. No Bloodborne game files are included.

## Remaining work

- Verify current website account/auth API in a staging environment, implement a safe device/browser sign-in flow and account UI.
- Add a versioned discovery/invite service contract with access controls, no public secret leaks and expiry.
- Preserve visy's encrypted BBP3 direct P2P, then test optional server-side relay **only when direct fails**.
- Full Windows render/gameplay check and two-PC real Internet test; cross-client shadPS4/BBSC interoperability requires protocol bridging, not merely the same server address.

## GitHub release channel isolation

The launcher update notifier (`scripts/update_check.py`) now only checks
`ProhorovIlja/bloodborne_pc_windows_port`. Its clickable update links are restricted to
the same repository's HTTPS release pages; a stale visy cache cannot point to visy releases.
This is **notification only**: it never downloads or replaces game binaries. The UI cache is
`seamless_hunt_update_check.json`, independent from the old visy cache. Until this fork
publishes a non-prerelease GitHub release, no update alert is expected.
