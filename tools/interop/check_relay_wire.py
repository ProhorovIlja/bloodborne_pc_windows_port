"""Offline BBR1 wire conformance: real CLS 0.0.2 server vs pinned native bbnet20.

Run ONLY against checked-out, pinned upstream sources. Do not bind UDP ports,
contact a production relay, create player accounts or modify any saves.
Exercising the actual official server's relay receiver is stronger evidence
than comparing textual descriptions of the two implementations, but it is NOT
proof that Bloodborne online gameplay or live crossplay works.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy
import socket
import struct

RELATIVE_CLS = "server/gameserver/bbhost_service.py"
RELATIVE_NATIVE = "gpu/bbnet20/vendor/shadps4/core/net/p2p_relay.cpp"


def _id(value: str) -> bytes:
    payload = value.encode("ascii")
    if not 1 <= len(payload) <= 16:
        raise ValueError("relay test ID outside 16-byte limit")
    return payload.ljust(16, b"\0")


def verify(official_root: Path, native_root: Path) -> dict:
    cls_source = Path(official_root) / RELATIVE_CLS
    native_source = Path(native_root) / RELATIVE_NATIVE
    if not cls_source.is_file() or not native_source.is_file():
        raise ValueError("both pinned CLS relay server and native P2P source are required")
    source = native_source.read_text(encoding="utf-8")
    # Fail closed on changes to the native relay frame layout. Check individual
    # source expressions, not variable line numbers or comments only.
    needed = {
        "BBR1 prefix": "constexpr u8 kMagic[4] = {'B', 'B', 'R', '1'};",
        "ID length": "constexpr size_t kIdSize = 16;",
        "endpoint length": "constexpr size_t kEpSize = 6;",
        "send opcode": "packet.push_back(0x03);",
        "sender ID": "packet.insert(packet.end(), self.begin(), self.end());",
        "endpoint bytes": "packet.insert(packet.end(), ep, ep + kEpSize);",
        "original payload": "packet.insert(packet.end(), wire.begin(), wire.end());",
        "relay output opcode": "if (data[4] != 0x04",
        "missing peer opcode": "if (data[4] == 0x05",
    }
    for name, signature in needed.items():
        if signature not in source:
            raise ValueError(f"native BBR1 wire source changed ({name}); compatibility review required")
    # The module does not call configure(), bind a socket or spawn threads when
    # loaded this way. Relay._send_packet is mocked with a list, not a socket.
    original = runpy.run_path(str(cls_source), run_name="bbsc_relay_wire_audit")
    if original.get("SHAD_MAGIC") != b"BBR1":
        raise ValueError("the official CLS server has a different relay version")
    relay = original["Relay"]()
    sent = []
    relay._send_packet = lambda frame, dest: sent.append((frame, dest))
    host = ("127.0.0.1", 31313)
    hunter = ("127.0.0.1", 31314)
    spoof = ("127.0.0.1", 31315)
    host_id = _id("NativeHunter")
    hunter_id = _id("ShadPS4Peer")
    relay._shad(b"BBR1\x01" + host_id, host)
    relay._shad(b"BBR1\x01" + hunter_id, hunter)
    if sent != [(b"BBR1\x02", host), (b"BBR1\x02", hunter)]:
        raise ValueError("CLS relay registration ACK differs from native client")
    sent.clear()
    ep = socket.inet_aton("198.51.100.42") + struct.pack("!H", 31313)
    game_wire = bytes.fromhex("01 40 00 00 aa bb cc dd 55 44 33")
    from_client = b"BBR1\x03" + hunter_id + host_id + ep + game_wire
    relay._shad(from_client, host)
    expected = b"BBR1\x04" + host_id + ep + game_wire
    if sent != [(expected, hunter)]:
        raise ValueError("official relay cannot forward native BBR1 P2P envelope byte-for-byte")
    sent.clear()
    relay._shad(from_client, spoof)
    if sent:
        raise ValueError("unregistered source address can spoof another hunter's frame")
    relay._shad(b"BBR1\x03" + _id("NotRegistered") + host_id + ep + game_wire, host)
    if sent != [(b"BBR1\x05" + _id("NotRegistered"), host)]:
        raise ValueError("missing-relay-peer response does not match native fallback")
    return {
        "server": "CLSAMG22/BBSC 0.0.2",
        "client": "deadinside28/bloodborne_pc bbnet20",
        "wire_protocol": "BBR1",
        "id_bytes": 16,
        "endpoint_bytes": 6,
        "scenarios": ["registration ACK", "original frame forwarding",
                      "source-address spoof refusal", "missing-peer response"],
        "gameplay_interoperability_verified": False,
        "live_server_contacted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.official, args.native), sort_keys=True))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
