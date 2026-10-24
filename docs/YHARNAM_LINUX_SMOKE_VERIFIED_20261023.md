# Yharnam Together on Fornex: Linux smoke test verified (2026-10-23)

## Evidence

Source checkout: `lKaniel/bloodborne-server` pinned to `77e350743a7cb4524cfcc1782fb6e3af64e25b15`.

- Ubuntu 24.04.5, GCC 13.3, CMake 3.28.3, Ninja 1.11.1.
- Qt 6.8.3 installed privately under `/srv/sh-yt-poc/Qt/6.8.3/gcc_64`; Qt6WebSockets was additionally required by Qt6HttpServer.
- Protobuf submodule checked out at `5917ee224a7e47383a78acc129628511fe210dff`.
- Compiled `shadnet`, `test_team_lobby` and `test_server_link`: Ninja reached **745/745**.
- Both tests **PASS**.
- Server launched successfully as unprivileged `shytpoc` with `SHADNET_HOME=/srv/sh-yt-poc/stage-smoke-20261023/state`, no production service change.
- Verified listeners: **127.0.0.1:32313/TCP**, **127.0.0.1:32314/UDP**, **127.0.0.1:32315/TCP**, **127.0.0.1:21443/TCP**.
- Log: SQLite migrations complete, 0 party worlds loaded, Bloodborne summon routes registered, WebAPI and Bloodborne backend listening, no startup errors shown.
- VPS observed with ~2.4 GiB available RAM and ~5.3 GB free disk.
- **No evidence yet** of remote network reachability, client compatibility, successful two-player session or performance at scale.

## Next: isolated tailnet test (NOT public production)

1. Stop the **smoke-test process only** using Ctrl+C in its SSH terminal.
2. Install/configure Tailscale on VPS and both Windows clients if not already connected, in a restricted tailnet with only invited testers. Be aware that by default other server services bound to `0.0.0.0` may also be reachable to tailnet members; enforce appropriate ACLs.
3. On the VPS check `tailscale ip -4`, `ip -4 addr show tailscale0`, and `ss -lnut | grep -E ':(32313|32314|32315|21443)'` (the staging ports must be free before launching the new instance).
4. Stage a **new**, empty directory, never edit the smoke-test instance:
```bash
TSIP="$(tailscale ip -4 | head -n 1)"
test -n "$TSIP" || exit 1
ip -o -4 addr show dev tailscale0 | grep -F "inet $TSIP/" || exit 1
runuser -u shytpoc -- env HOME=/srv/sh-yt-poc \
  python3 /srv/sh-yt-poc/prepare_staging.py \
  --checkout /srv/sh-yt-poc/upstream \
  --stage /srv/sh-yt-poc/stage-tailnet-20261023 \
  --bind "$TSIP" --advertise "$TSIP" \
  --binary /srv/sh-yt-poc/build/shadnet
```
5. Run foreground without registering a service:
```bash
runuser -u shytpoc -- env HOME=/srv/sh-yt-poc \
  LD_LIBRARY_PATH=/srv/sh-yt-poc/Qt/6.8.3/gcc_64/lib \
  SHADNET_HOME=/srv/sh-yt-poc/stage-tailnet-20261023/state \
  /srv/sh-yt-poc/stage-tailnet-20261023/bin/shadnet
```
6. Confirm the UDP/TCP listeners bind only to the VPS's Tailscale address. From both testers, verify Tailscale reachability and TCP ports **32315** and **21443**.

### Windows client requirement

The stock Yharnam Together launcher uses `31314/31315/20443`, not the staged ports. The existing PoC includes `patch_launcher_ports.py`, which patches the **source** `bbport/launcher/bbport_coop.py` to support the environment variables `SH_YT_UDP_PORT=32314`, `SH_YT_WEBAPI_PORT=32315`, `SH_YT_BACKEND_PORT=21443`, `SH_YT_TCP_PORT=32313`. It does **not** patch an already installed `BLauncher.exe`. Build both Windows clients from the same pinned upstream source revision before testing. Avoid unattended launcher updates during these controlled version-matching tests. Use isolated test saves.

### Safety

Never change production listeners, stop production services, copy production databases, share production credentials, or open test traffic to the public Internet for this PoC. Current `TcpLocalOnly=true` keeps the test shadNet TCP listener on loopback. Don't claim crossplay with CLS or five players without gameplay tests.
