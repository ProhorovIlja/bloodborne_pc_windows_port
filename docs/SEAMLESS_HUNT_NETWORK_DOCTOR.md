# Seamless Hunt: Network Doctor (developer preview)

The single native-client fork contains an optional **Network doctor** button in **Party → Connection**. It verifies server reachability and can perform a separate, opt-in one-shot BBSC account check. It is NOT game matchmaking or an in-game BBSC login.

## What it checks

1. Real binary shadNet protocol v1 `ServerInfo` greeting from the chosen realm host on TCP 31313, plus a TCP Web API check on port 31315. No credentials are sent by Network doctor.
2. `HEAD /ss.info` against GameServer `:20443` (expected `200 text/plain`, read-only).
3. RFC 5389 UDP STUN Binding Request against **the player's configured STUN server** (by default, `stun.l.google.com:19302`). It validates STUN cookie, transaction ID, attribute length, and mapped IPv4/IPv6 endpoint. It never logs the public IP.
4. IPv6 OS route availability by using `connect()` on a UDP socket, without sending a packet.

All checks are initiated manually and done in a background thread. The selected hostname is kept in `launcher_settings.json` under `seamless_hunt_host`, but is NOT yet passed to the gameplay engine; the regular visy direct P2P networking, DHT, password protection, saves and game files are unchanged.

**Privacy:** the STUN server necessarily sees the computer's external IP/UDP source port. Don't run if you do not consent; set STUN to `off` to skip UDP. The source IP is not written to the launcher log. No game passwords, identity tokens or BBP3 party codes are sent.

**Interpretation:** working TCP and STUN do not establish that NAT punching works end-to-end. The IPv6 check only confirms a configured route. In particular it does not measure relay selection, packet loss or latency between two hunters. The definitive network validation remains a two-PC Internet host/join test using the *same current native build*.

## Account checks and private registration

**Account website** opens `https://seamlesshunt.com` in the default browser for creating accounts on the public Seamless Hunt realm. **Check BBSC login...** creates a short-lived connection using the actual published shadNet `LoginRequest` protobuf and parses the Login reply, then disconnects. It does not acquire or retain gameplay tokens, sign in the Bloodborne executable, or use the bells.

**Private account...** creates an account on a privately hosted shadNet/BBSC server using the published `Create` request and optional server registration secret. Public Seamless Hunt registration is intentionally redirected to the website. Credentials and registration keys are never written to launcher settings, stored in process arguments or included in logs. The text fields are cleared upon submit.

**Security: shadNet sends login and registration credentials over unencrypted TCP, according to upstream shadPS4/BBSC sources.** These account actions require explicit user confirmation and should only be used for a server the player trusts. The real native gameplay integration will also need to address network trust and token life cycle.

## Development

Run locally, with no game installation:

```sh
python scripts/seamless_hunt.py
python scripts/seamless_hunt_network.py --stun off
python scripts/seamless_hunt_network.py --stun stun.l.google.com:19302
python -m unittest discover -s tests -p 'test_seamless_hunt.py' -v
python -m unittest discover -s tests -p 'test_seamless_hunt_network.py' -v
python -m unittest discover -s tests -p 'test_bbsc_shadnet_wire.py' -v
python -m unittest discover -s tests -p 'test_shadnet_account.py' -v
python -m unittest discover -s tests -p 'test_shadnet_registration.py' -v
```

Tests use fake sockets, never a live production network. They run under GitHub Actions on **Ubuntu and Windows**.

## Building the Windows native runtime

The `Native Windows engine build` workflow is a separate developer CI job under `.github/workflows/native-windows-build.yml`. It initializes the original git submodules and uses MSYS2 CLANG64. The `tools/setup_windows_deps.sh` helper pins magic_enum, miniz and shadPS4's xbyak headers to exact source commits. Windows CMake uses them without silently replacing vendor code. Build result, if successful, is a **developer-only archive with binaries** from the GitHub Actions artifacts, not a game-ready distribution and not proof of in-game play. No Bloodborne game files are included.

## Remaining work

- Integrate actual shadNet account login, NP/matching/signaling and BBSC hooks into native gameplay. The separate account check is not equivalent to an in-game login.
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
