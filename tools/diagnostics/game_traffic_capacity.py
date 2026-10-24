#!/usr/bin/env python3
"""Estimate GAME-DATAGRAM relay bandwidth for hypothetical Bloodborne parties.

Important: Yharnam Together's pinned team netcode sends game frames through
shadNet (one UDP link per client). This tool models one class of traffic; it
does NOT measure real game load, Qt server CPU, RAM, world-state traffic, NAT,
or RTT. Hybrid direct P2P is a design scenario, NOT an implemented feature.

The estimate assumes each hunter sends K decimal kilobits/second of game
payload and shadNet relays that payload to each of the other (N - 1) hunters.
This is a capacity-planning lower bound if optional protocol retransmits,
world state and relay encapsulation overhead are not included.
"""
from __future__ import annotations

import argparse
import json
import math


def estimate(*, hunters: int, parties: int, hunter_payload_kbps: float,
             direct_fraction: float = 0.0, overhead_fraction: float = 0.0) -> dict:
    if type(hunters) is not int or not 2 <= hunters <= 8:
        raise ValueError("hunters must be an integer between 2 and 8")
    if type(parties) is not int or not 1 <= parties <= 100000:
        raise ValueError("parties must be a positive bounded integer")
    if not math.isfinite(hunter_payload_kbps) or not 0 < hunter_payload_kbps <= 100000:
        raise ValueError("client payload rate must be finite and positive in kbit/s")
    if not math.isfinite(direct_fraction) or not 0 <= direct_fraction <= 1:
        raise ValueError("direct fraction must be within 0..1")
    if not math.isfinite(overhead_fraction) or not 0 <= overhead_fraction <= 3:
        raise ValueError("overhead fraction must be within 0..3")
    # Server-world/control bytes are NOT represented here: a direct path
    # never makes server ingress or CPU truly zero.
    payload_to_relay = parties * hunters * hunter_payload_kbps * (1.0 - direct_fraction)
    game_egress = payload_to_relay * (hunters - 1)
    game_ingress = payload_to_relay
    factor = 1.0 + overhead_fraction
    client_direct_game_egress = (
        parties * hunters * (hunters - 1) * hunter_payload_kbps * direct_fraction
    )
    return {
        "transport": "server_relay" if direct_fraction == 0 else "HYPOTHETICAL hybrid direct P2P",
        "current_upstream_mode": "server_relay_udp",
        "direct_p2p_in_pinned_game_verified": False,
        "clients": parties * hunters,
        "hunters_per_party": hunters,
        "parties": parties,
        "assumed_per_hunter_game_payload_kbps": hunter_payload_kbps,
        "assumed_datagram_overhead_fraction": overhead_fraction,
        "assumed_direct_p2p_share": direct_fraction,
        "server_relay_game_ingress_mbps": round(game_ingress * factor / 1000, 6),
        "server_relay_game_egress_mbps": round(game_egress * factor / 1000, 6),
        "clients_total_direct_game_egress_mbps": round(client_direct_game_egress * factor / 1000, 6),
        "world_state_control_bytes_included": False,
        "server_cpu_ram_rtt_loss_measured": False,
        "release_ready": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hunters", type=int, required=True, help="Hunters per room (2 to 8)")
    p.add_argument("--parties", type=int, required=True, help="Simultaneous rooms")
    p.add_argument("--per-hunter-kbps", type=float, required=True,
                   help="Assumed per-client game payload in decimal kbit/s, NOT an observed metric")
    p.add_argument("--overhead-pct", type=float, default=0.0,
                   help="Explicit estimated encapsulation/retransmit overhead percent")
    p.add_argument("--experimental-direct-pct", type=float, default=0.0,
                   help="Hypothetical direct P2P fraction: NOT currently implemented")
    p.add_argument("--allow-hypothetical-p2p", action="store_true",
                   help="Acknowledges that nonzero direct fraction is ONLY a model")
    args = p.parse_args()
    if args.experimental_direct_pct and not args.allow_hypothetical_p2p:
        p.error("P2P is not in the current Yharnam Together netcode: supply --allow-hypothetical-p2p only for capacity modeling")
    try:
        result = estimate(hunters=args.hunters, parties=args.parties,
                          hunter_payload_kbps=args.per_hunter_kbps,
                          direct_fraction=args.experimental_direct_pct / 100,
                          overhead_fraction=args.overhead_pct / 100)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
