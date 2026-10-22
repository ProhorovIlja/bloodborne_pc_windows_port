"""Opt-in, privacy-conscious P2P connectivity diagnostics for Seamless Hunt.

The current native game's direct P2P remains unchanged. This module ONLY:
  * sends one RFC 5389 Binding Request to the configured STUN server;
  * inspects local IPv6 routing without transmitting any IPv6 packets.

A STUN success proves an outbound UDP reply reached this PC; it DOES NOT
prove hole-punching will work, identify the NAT type, or verify BBP3 co-op.
A STUN server learns the source IP/port from the request. The UI never logs it.

No third-party dependencies. All packet decoding enforces bounds and the
transaction ID before accepting an address.
"""
from __future__ import annotations

import ipaddress
import secrets
import socket
import struct
import time
from dataclasses import dataclass

from seamless_hunt import validate_host

COOKIE = 0x2112A442
BIND_REQUEST = 0x0001
BIND_SUCCESS = 0x0101
XOR_MAPPED = 0x0020
MAPPED = 0x0001
MAX_PACKET = 4096
DEFAULT_STUN = "stun.l.google.com:19302"
IPV6_ROUTE_TARGET = "2606:4700:4700::1111"


@dataclass(frozen=True)
class RouteCheck:
    label: str
    state: str  # "ok", "warning", "off"
    message: str
    latency_ms: int | None = None

    def __post_init__(self):
        if self.state not in ("ok", "warning", "off"):
            raise ValueError("Invalid route-check state")


def parse_stun_target(value: str) -> tuple[str, int] | None:
    """Supports hostname:port, IPv4:port and [IPv6]:port; 'off' disables STUN."""
    if not isinstance(value, str):
        raise ValueError("STUN must be a host and optional port")
    target = value.strip()
    if not target or target.lower() == "off":
        return None
    if any(ch.isspace() for ch in target):
        raise ValueError("STUN address cannot contain whitespace")
    if target.startswith("["):
        end = target.find("]")
        if end < 0:
            raise ValueError("Missing closing IPv6 bracket")
        host = validate_host(target[:end + 1])
        rest = target[end + 1:]
        if rest and not rest.startswith(":"):
            raise ValueError("Invalid STUN port")
        port_text = rest[1:] if rest else ""
    else:
        if target.count(":") > 1:
            raise ValueError("IPv6 address must use [brackets]")
        host, sep, port_text = target.partition(":")
        host = validate_host(host)
        if sep and not port_text:
            raise ValueError("Empty STUN port")
    if port_text and not port_text.isascii():
        raise ValueError("Port must be ASCII digits")
    if port_text and not port_text.isdecimal():
        raise ValueError("Port must be numeric")
    port = int(port_text) if port_text else 3478
    if port < 1 or port > 65535:
        raise ValueError("STUN port must be 1..65535")
    return host, port


def _mapped_address(packet: bytes, tx_id: bytes) -> tuple[str, int] | None:
    """Decode a verified STUN response, including XOR-MAPPED-ADDRESS IPv4/v6."""
    if len(packet) < 20:
        return None
    kind, size, cookie = struct.unpack_from("!HHI", packet)
    if kind != BIND_SUCCESS or cookie != COOKIE or packet[8:20] != tx_id:
        return None
    if size % 4 or size > MAX_PACKET - 20 or len(packet) < 20 + size:
        return None
    end = 20 + size
    index = 20
    plain = None
    while index + 4 <= end:
        attr, n = struct.unpack_from("!HH", packet, index)
        index += 4
        if index + n > end:
            return None
        value = packet[index:index + n]
        index += (n + 3) & ~3
        if index > end:
            return None
        if attr not in (XOR_MAPPED, MAPPED) or n not in (8, 20) or value[0:1] != b"\x00":
            continue
        family = value[1]
        if (family == 1 and n != 8) or (family == 2 and n != 20) or family not in (1, 2):
            continue
        encoded_port = struct.unpack_from("!H", value, 2)[0]
        if attr == XOR_MAPPED:
            port = encoded_port ^ (COOKIE >> 16)
            xor_key = struct.pack("!I", COOKIE) + tx_id
            raw_addr = bytes(a ^ b for a, b in zip(value[4:], xor_key))
        else:
            port = encoded_port
            raw_addr = value[4:]
        try:
            addr = str(ipaddress.ip_address(raw_addr))
        except ValueError:
            continue
        if port < 1:
            continue
        if attr == XOR_MAPPED:
            return addr, port
        plain = (addr, port)
    return plain


def probe_udp_stun(value: str = DEFAULT_STUN, timeout: float = 2.0) -> RouteCheck:
    """One bounded Binding Request, no gameplay, passwords or port forwarding."""
    try:
        endpoint = parse_stun_target(value)
    except ValueError as exc:
        return RouteCheck("UDP/STUN", "warning", f"Invalid STUN setting: {exc}")
    if endpoint is None:
        return RouteCheck("UDP/STUN", "off", "disabled in Party settings")
    host, port = endpoint
    timeout = min(5.0, max(0.2, timeout))
    tx_id = secrets.token_bytes(12)
    request = struct.pack("!HHI", BIND_REQUEST, 0, COOKIE) + tx_id
    started = time.monotonic()
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
    except OSError:
        return RouteCheck("UDP/STUN", "warning", "STUN DNS lookup failed")
    last_failure = "No STUN reply (UDP blocked, endpoint unreachable or timed out)"
    for family, stype, protocol, _, sockaddr in addresses[:4]:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        try:
            with socket.socket(family, stype, protocol) as conn:
                conn.settimeout(timeout)
                conn.sendto(request, sockaddr)
                packet, sender = conn.recvfrom(MAX_PACKET)
                # Ignore forged packets from another source, with no second retry.
                if sender[0] != sockaddr[0] or sender[1] != sockaddr[1]:
                    last_failure = "STUN reply came from a different endpoint"
                    continue
                mapped = _mapped_address(packet, tx_id)
                if mapped is None:
                    last_failure = "STUN reply did not match the request"
                    continue
                ip = ipaddress.ip_address(mapped[0])
                if ip.is_unspecified or ip.is_loopback or ip.is_multicast:
                    last_failure = "STUN returned an unusable mapped address"
                    continue
                latency_ms = round((time.monotonic() - started) * 1000)
                return RouteCheck("UDP/STUN", "ok",
                                  f"UDP reply received, public mapping discovered (IPv{ip.version}); "
                                  "NAT traversal not yet verified", latency_ms)
        except (OSError, TimeoutError):
            pass
    return RouteCheck("UDP/STUN", "warning", last_failure)


def probe_ipv6_route() -> RouteCheck:
    """Check OS routing via connect() on a UDP socket; send NO network packets."""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as conn:
            conn.connect((IPV6_ROUTE_TARGET, 443, 0, 0))
            local_ip = ipaddress.IPv6Address(conn.getsockname()[0].split("%")[0])
            if local_ip.is_loopback or local_ip.is_link_local or local_ip.is_unspecified:
                return RouteCheck("IPv6", "warning", "No usable non-local IPv6 route")
            return RouteCheck("IPv6", "ok",
                              "IPv6 route configured; peer reachability not verified")
    except (OSError, ValueError):
        return RouteCheck("IPv6", "warning", "No usable IPv6 route on this PC")


def check_routes(stun_server: str = DEFAULT_STUN, timeout: float = 2.0) -> list[RouteCheck]:
    return [probe_udp_stun(stun_server, timeout), probe_ipv6_route()]


def format_routes(rows: list[RouteCheck]) -> str:
    return "; ".join(f"{row.label}: {row.message}"
                     + (f" ({row.latency_ms} ms)" if row.latency_ms is not None else "")
                     for row in rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Optional STUN/IPv6 checks, no login and no game traffic")
    parser.add_argument("--stun", default=DEFAULT_STUN)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()
    for result in check_routes(args.stun, args.timeout):
        print(f"{result.label}: {result.message}")
    print("Success here is not proof that two players can connect directly.")
