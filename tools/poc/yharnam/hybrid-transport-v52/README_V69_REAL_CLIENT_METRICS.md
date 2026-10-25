# V69: actual native game's shadNet / direct UDP transport telemetry

**Development-only. Not a claim that Direct P2P or the native Windows game runs yet.**

This patch installs into the original `emulator/src/core/libraries/network/p2p_sockets.cpp` during pinned `compose_sources.py --upstream ... --repo ... --out ...` assembly. The original `P2PTransport::SendFrame` still uses `Link::RoutesThroughServer` and the original `Link::EncodeData` / `Transmit` behavior. Incoming `OnLinkDatagram(Kind::Data)` still passes decoded data to `Deliver` without modification.

By default no tracking or periodic logging takes place. In a future **compiled native client** test launch with `SHYT_ROUTE_METRICS=1` in that client's environment:

PowerShell (development client only):
```powershell
$env:SHYT_ROUTE_METRICS = '1'
# Launch the future compiled development client from THIS PowerShell session.
# Keep actual game executable/path private if proprietary files are involved.
```

Linux development client:
```bash
SHYT_ROUTE_METRICS=1 ./YOUR_DEV_CLIENT
```

No changes to the live Fornex server are required. The game emits one aggregate log record every 30 seconds **when there is native game UDP traffic**. It does not log credentials, account names, peer IPs or packet payloads.

Fields:
- `relay_out`: number/bytes of `P2PTransport::SendFrame` datagrams **submitted** to existing shadNet UDP routing (includes SHLK envelope overhead).
- `relay_game_out`: of those, frames whose original payload matched native `SHAD` type 0x40; counts full submitted encoded datagram bytes (not the original net payload size).
- `relay_in`: server `SHLK` Data frames actually accepted and decoded from shadNet; counts the incoming UDP datagram size.
- `native_direct_out`: existing transport's packets not routed via shadNet. They are **not evidence of authenticated new hybrid Direct P2P**, merely non-server `SendFrame` submissions.
- `native_direct_in`: currently zero, because the original `ReceiveMain` rejects unsolicited direct peer datagrams; future trusted direct ingress may increment only after authenticated acceptance.
- `tx_failures`: synchronous `P2PTransport::Transmit` rejection (note simulated link cuts and queued-delay sends may report accepted even when packets are not actually delivered).

**Important limitations:** counters are per-game client process and cumulative. They count submissions to `Transmit`, not guaranteed on-wire delivery or physical network interface bytes; delayed and intentionally dropped test traffic affect comparisons. Counters cannot measure VPS CPU consumption by themselves, P2P grant effectiveness, remote bandwidth, or 200-user concurrency. Correlate over fixed windows with independently observed Fornex CPU, `ss`/network counters, game frame time, peer RTT/jitter, number of players and direct-vs-relay path ratio, with privacy-aware sampling.

This source is guarded by pinned upstream and CI; **no command enables a P2P session or changes server config**. Full Windows client build/testing remains a separate gate.
