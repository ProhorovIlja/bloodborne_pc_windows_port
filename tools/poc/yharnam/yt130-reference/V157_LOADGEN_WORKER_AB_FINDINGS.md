# V157: original Qt/Redis 200-hunter loader-process A/B, source-evidence report

**Real original YT1.3 source**, `0645740a33ae21c56df3b4a0d9777086dbca6053`, CI [#41094188895](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41094188895) **SUCCESS as a diagnostic job**, artifact **12996342884**, `yt130-V157-200-player-real-Qt-loadgen-4-8-16-worker-A-B-DIAGNOSTIC`. This does **not** mean game delivery passed. The exact original Qt/Redis/shadNet server and YT bbload tool were used, the same 200 simulated hunters in 40 five-seat teams and the same test harness run time / enemy owner FPS. Only the **number of bbload client processes**, each owning multiple UDP sockets, varied.

| Real Qt server setup | bbload processes | Playing | Complete teams | min steady window | steady game entries delivered | all sent / received game entries | observed server Qt kind3 UDP in=out |
|---|---:|---:|---:|---:|---:|---:|---|
| One shard, 5 enemy owners | 4 | 200/200 | 40/40 | 21,704 ms | **85.65%** | 1,868,020 / 1,629,799 | 635,460=635,460 |
| One shard, 5 enemy owners | 8 | 200/200 | 40/40 | 12,317 ms | **82.24%** | 1,896,732 / 1,620,171 | 633,800=633,800 |
| One shard, 5 enemy owners | 16 | 200/200 | 40/40 | 16,261 ms | **88.84%** | 1,601,052 / 1,436,898 | 534,988=534,988 |
| Three shards, code join, 1 owner | 4 | 200/200 | 40/40 | 16,606 ms | **96.94%** | 446,360 / 436,885 | 223,412=223,412 |
| Three shards, code join, 1 owner | 16 | **175/200** | **35/40** | 0 ms | **96.73%** (not valid as steady capacity) | 400,748 / 387,898 | 197,192=197,192 |

**Observed original server/team responses, count-only:** one shard 5 owners, 4 workers `team_other_notice=0`, 8 workers `8`, 16 workers `112`. Three-shard code join, 4 workers `8`, 16 workers `34`. All runs `team_name_absent=0`, `team_name_ambiguous=0`, `team_lookup_throttled=0`. No raw refusal text, usernames, codes, access tokens or IP addresses were emitted. The `team_other_notice` values are **reply observations**, not unique failed players, and include potentially benign repeated team requests. V159 adds bounded original source-exact classifications for `no such invite`, `no team has that code`, `team full`, `already joined`, `create team first`, `world gone`, and unknown other. V159 source-only CI [#41097312033](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41097312033) SUCCESS. Do not claim which category dominates before a real V159 load test.

**Network observations:** all five scenarios had zero bbload immediate UDP write failures or shorts, zero measured Linux host UDP receive-buffer errors, and matching sampled Qt LinkServer kind3 ingress/successful outgoing writes. This neither proves no receiver socket drops nor proves the relay loses game entries: a single Data datagram can contain multiple game entries and the Qt wire sampler reports 5s windows. Five-owner cases had `packets_lost` sequence gaps 125,040, 123,969 and 110,639 (4/8/16 worker cases); three-shard 1-owner reports `packets_lost=0` while game-entry totals still differ. The latter is consistent with losses at start/end or missing sender/receiver readiness and cannot locate the actual cause.

## Conclusion

**Increasing simulated client-process parallelism alone does not resolve the 15–18% five-owner game-entry deficit.** Treat 4/8/16 as an A/B within one runner, not as statistically controlled performance benchmarking: team readiness and steady windows vary. 16 workers makes the cross-shard code-join case *less* reliable on this sample (25 in Lobby, min steady 0). Do not weaken the unchanged 99% strict game-data QoS target, 200 Playing / 40 complete five-hunter teams, or previous invitation diagnostics.

## Next narrowing checks already staged

- **V158** exact original Qt `Game::OnReadyRead`, `ServerLink::DecodeData` and `DecodeGameFrame` diagnostic counters. Counts actual read errors, short reads, successfully opened Data datagrams, malformed Data, bad SHAD frame headers, game-frame decoding failures, short embedded entries and decoded frames, **with no payloads or identities**. Original source regression CI [#41096445994](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41096445994) SUCCESS; an integrated real Qt A/B includes these counters in future evidence but no result is claimed until it completes.
- **V159** separate reasons for observed non-name lobby notices from original `team_lobby.cpp`, allowing us to distinguish benign repeated requests from missing codes/invites, full teams, or world failures. Source-only original YT staging CI #41097312033 SUCCESS.
- **Real loopback validation:** V158+V159 are being integrated into another original Qt 200-player worker test; any report failing count reconciliations is invalid, not a successful server.

**No production Fornex deployment, real two-PC P2P benchmark, full campaign, or public server capacity claim is supported by these measurements.**
