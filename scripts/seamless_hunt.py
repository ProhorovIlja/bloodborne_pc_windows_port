"""Read-only Seamless Hunt connectivity diagnostics for the native PC launcher.

Uses the ports and /ss.info handler of the 2026-10-22 Seamless Hunt server
handoff. This is NOT matchmaking, account sign-in, or party protocol bridging.
Never sends passwords, tokens, party codes, or game traffic.

Standard library only: usable with the embedded Python shipped by bbport.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import http.client
import ipaddress
import json
import re
import socket
import time

DEFAULT_HOST = "play.seamlesshunt.com"
TCP_SERVICES = (("shadNet", 31313), ("Web API", 31315))
GAME_SERVER_PORT = 20443


@dataclass(frozen=True)
class ServiceResult:
    name: str
    port: int
    reachable: bool
    latency_ms: int | None
    detail: str

    def as_dict(self) -> dict:
        return {"service": self.name, "port": self.port, "reachable": self.reachable,
                "latency_ms": self.latency_ms, "detail": self.detail}


def validate_host(host: str) -> str:
    """Only a DNS hostname or IP, not a URL, embedded port or HTTP header."""
    if not isinstance(host, str) or not host or host != host.strip() or len(host) > 253:
        raise ValueError("Enter a DNS hostname or IP address")
    if any(c in host for c in "/\\@?#%") or any(c.isspace() for c in host):
        raise ValueError("Host must not contain a URL, port, path or whitespace")
    # Support an IPv6 literal only if enclosed in brackets; no zone IDs.
    if host.startswith("[") and host.endswith("]"):
        return str(ipaddress.IPv6Address(host[1:-1]))
    if ":" in host or "[" in host or "]" in host:
        raise ValueError("Use a hostname, IPv4 or bracketed IPv6 address without a port")
    try:
        return str(ipaddress.IPv4Address(host))
    except ValueError:
        pass
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
        raise ValueError("Invalid hostname")
    if any(not part or part.startswith("-") or part.endswith("-") or len(part) > 63
           for part in host.split(".")):
        raise ValueError("Invalid DNS label")
    return host.lower()


def _short_error(exc: Exception) -> str:
    # Avoid leaking user-specific IPs/paths in the GUI or support bundle.
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, socket.gaierror):
        return "DNS lookup failed"
    if isinstance(exc, ConnectionRefusedError):
        return "connection refused"
    if isinstance(exc, OSError):
        return "network unavailable or connection refused"
    return "unexpected response"


def probe_tcp(host: str, name: str, port: int, timeout: float = 1.5) -> ServiceResult:
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        ms = round((time.monotonic() - start) * 1000)
        return ServiceResult(name, port, True, ms, "TCP reachable (not authenticated)")
    except (OSError, TimeoutError) as exc:
        return ServiceResult(name, port, False, None, _short_error(exc))


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        block = conn.recv(size - len(data))
        if not block:
            raise ConnectionError("shadNet disconnected before greeting completed")
        data.extend(block)
    return bytes(data)


def probe_shadnet(host: str, port: int = 31313, timeout: float = 1.5) -> ServiceResult:
    """Validate protocol v1 ServerInfo. Send no account info or game traffic."""
    from bbsc_shadnet_wire import (HEADER_BYTES, ShadNetProtocolError,
                                   parse_header, parse_greeting)
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(timeout)
            header = _recv_exact(conn, HEADER_BYTES)
            _, _, total, _ = parse_header(header)
            payload = _recv_exact(conn, total - HEADER_BYTES)
            greeting = parse_greeting(header, payload)
            return ServiceResult("shadNet", port, True,
                                 round((time.monotonic() - start) * 1000),
                                 f"shadNet protocol v{greeting.version} greeting OK; "
                                 "account and BBSC gameplay not verified")
    except ShadNetProtocolError:
        return ServiceResult("shadNet", port, False, None,
                             "unexpected shadNet greeting or protocol version")
    except (OSError, TimeoutError, ConnectionError) as exc:
        return ServiceResult("shadNet", port, False, None, _short_error(exc))


def probe_game_server(host: str, timeout: float = 1.5) -> ServiceResult:
    """HEAD is handled without a response body by the deployed game's /ss.info route."""
    start = time.monotonic()
    conn = http.client.HTTPConnection(host, GAME_SERVER_PORT, timeout=timeout)
    try:
        conn.request("HEAD", "/ss.info", headers={"User-Agent": "SeamlessHunt-Native-Check/1",
                                                  "Connection": "close"})
        response = conn.getresponse()
        ms = round((time.monotonic() - start) * 1000)
        ok = response.status == 200 and response.getheader("Content-Type", "").lower().startswith("text/plain")
        detail = "GameServer /ss.info reachable" if ok else f"unexpected HTTP {response.status}"
        return ServiceResult("GameServer", GAME_SERVER_PORT, ok, ms, detail)
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        return ServiceResult("GameServer", GAME_SERVER_PORT, False, None, _short_error(exc))
    finally:
        conn.close()


def check_services(host: str = DEFAULT_HOST, timeout: float = 1.5) -> list[ServiceResult]:
    """Opt-in check only; never run automatically or send credentials."""
    host = validate_host(host)
    timeout = min(5.0, max(0.2, float(timeout)))
    result = [probe_shadnet(host, 31313, timeout),
              probe_tcp(host, "Web API", 31315, timeout)]
    result.append(probe_game_server(host, timeout))
    return result


def format_results(results: list[ServiceResult]) -> str:
    return "; ".join(f"{r.name} {r.port}: {'OK' if r.reachable else r.detail}"
                     + (f" ({r.latency_ms} ms)" if r.latency_ms is not None and r.reachable else "")
                     for r in results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Seamless Hunt connectivity check (no credentials)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="hostname only, without scheme or port")
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        results = check_services(args.host, args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps({"host": validate_host(args.host), "services": [r.as_dict() for r in results]}))
    else:
        print(f"{args.host}: {format_results(results)}")
        print("This checks connectivity only; it does not validate accounts, P2P, or cross-client play.")
    return 0 if all(r.reachable for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
