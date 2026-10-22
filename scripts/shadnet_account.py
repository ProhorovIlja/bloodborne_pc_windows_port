"""Opt-in shadNet protocol-v1 account sign-in check for BBSC.

This uses the exact *published* CLSAMG22/BBSC protocol framing, LoginRequest
protobuf field numbers, and Login error codes. It opens a separate short-lived
TCP connection, signs in, reads the result, then DISCONNECTS. It cannot log
the GAME in or join other hunters. Login check while playing may receive
"already logged in"; use this only while the game is closed.

Security note: the upstream shadNet wire protocol uses bare TCP, not TLS.
Therefore passwords are transmitted unencrypted, exactly as in the upstream
shadPS4 client. Only connect to a server you trust. No passwords are stored,
logged, put into process arguments or written to any file by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import socket
import struct

from bbsc_shadnet_wire import HEADER_BYTES, ShadNetProtocolError, parse_greeting

MAX_REPLY = 1_048_576
MAX_PROTO = 1_048_576
DEFAULT_PORT = 31313
LOGIN_ERRORS = {
    0: "Login accepted",
    1: "Malformed packet",
    2: "Invalid request",
    3: "Invalid input",
    4: "Too many attempts; try again later",
    5: "Login rejected",
    6: "This account is already logged in",
    7: "Username does not exist",
    8: "Incorrect password",
    9: "Invalid saved token",
    23: "Unauthorized",
    24: "Server database failure",
}
NAME_RE = re.compile(r"[A-Za-z0-9_-]{1,32}\Z")


@dataclass(frozen=True)
class AuthResult:
    accepted: bool
    status: str
    error_code: int | None = None
    user_id: int | None = None


def _varint(num: int) -> bytes:
    if not 0 <= num <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("protobuf number out of range")
    out = bytearray()
    while num > 0x7F:
        out.append((num & 0x7F) | 0x80)
        num >>= 7
    out.append(num)
    return bytes(out)


def _string_field(number: int, value: str) -> bytes:
    b = value.encode("utf-8")
    return _varint((number << 3) | 2) + _varint(len(b)) + b


def make_login_request(username: str, password: str) -> bytes:
    """Return a framed shadNet LoginRequest, not a key or token."""
    if not NAME_RE.fullmatch(username or ""):
        raise ValueError("Username must be 1-32 letters, numbers, _ or -")
    if not isinstance(password, str) or not password or len(password.encode("utf-8")) > 1024:
        raise ValueError("Password must be 1-1024 UTF-8 bytes")
    # Proto schema shadnet/LoginRequest (fields 1 npid, 2 password,
    # 4 title_id, 5 title_name). No token and no 'appear offline' setting.
    pb = (_string_field(1, username) + _string_field(2, password)
          + _string_field(4, "CUSA03173") + _string_field(5, "Bloodborne"))
    body = struct.pack("<I", len(pb)) + pb
    return struct.pack("<BHIQ", 0, 0, HEADER_BYTES + len(body), 1) + body


def _recv_exact(conn: socket.socket, amount: int) -> bytes:
    if amount < 0 or amount > MAX_REPLY:
        raise ShadNetProtocolError("invalid packet length")
    data = bytearray()
    while len(data) < amount:
        block = conn.recv(amount - len(data))
        if not block:
            raise ConnectionError("server disconnected")
        data.extend(block)
    return bytes(data)


def _frame(conn: socket.socket, *, limit: int = MAX_REPLY) -> tuple[int, int, int, bytes]:
    header = _recv_exact(conn, HEADER_BYTES)
    kind, command, size, req_id = struct.unpack("<BHIQ", header)
    if size < HEADER_BYTES or size > limit:
        raise ShadNetProtocolError("invalid server response size")
    return kind, command, req_id, _recv_exact(conn, size - HEADER_BYTES)


def _read_varint(data: bytes, off: int) -> tuple[int, int]:
    result = 0
    for bit in range(0, 70, 7):
        if off >= len(data):
            raise ShadNetProtocolError("truncated protobuf varint")
        octet = data[off]
        off += 1
        result |= (octet & 0x7F) << bit
        if octet < 0x80:
            if result > 0xFFFFFFFFFFFFFFFF:
                raise ShadNetProtocolError("protobuf varint overflow")
            return result, off
    raise ShadNetProtocolError("protobuf varint too long")


def _parse_login_user_id(payload: bytes) -> int | None:
    """Read LoginReply.user_id (field 2) without a protoc dependency.

    Skip all other fields including nested friends, with strict bounds.
    """
    i = 0
    found = None
    while i < len(payload):
        tag, i = _read_varint(payload, i)
        field, typ = tag >> 3, tag & 7
        if field == 0:
            raise ShadNetProtocolError("illegal protobuf tag")
        if typ == 0:
            value, i = _read_varint(payload, i)
            if field == 2:
                found = value
        elif typ == 1:
            i += 8
        elif typ == 2:
            count, i = _read_varint(payload, i)
            i += count
        elif typ == 5:
            i += 4
        else:
            raise ShadNetProtocolError("unsupported protobuf wire type")
        if i > len(payload):
            raise ShadNetProtocolError("truncated protobuf field")
    return found


def _login_result_payload(payload: bytes) -> AuthResult:
    if not payload:
        raise ShadNetProtocolError("empty Login reply")
    error = payload[0]
    if error:
        return AuthResult(False, LOGIN_ERRORS.get(error, f"Login rejected (code {error})"), error)
    if len(payload) < 5:
        raise ShadNetProtocolError("no LoginReply protobuf")
    (size,) = struct.unpack_from("<I", payload, 1)
    if size > MAX_PROTO or size != len(payload) - 5 or size == 0:
        raise ShadNetProtocolError("malformed LoginReply protobuf length")
    user_id = _parse_login_user_id(payload[5:])
    if user_id is None:
        raise ShadNetProtocolError("LoginReply lacks user ID")
    return AuthResult(True, "Login accepted (diagnostic connection closed)", 0, user_id)


def check_account(host: str, username: str, password: str,
                  *, port: int = DEFAULT_PORT, timeout: float = 4.0) -> AuthResult:
    """Connect, auth once, close. Does NOT retain credentials or WebAPI tokens."""
    # Imported lazily to avoid import loops with the connection doctor.
    from seamless_hunt import validate_host
    host = validate_host(host)
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Invalid shadNet port")
    if not 0.5 <= timeout <= 10.0:
        raise ValueError("Timeout must be between 0.5 and 10 seconds")
    pkt = make_login_request(username, password)
    # Don't include socket exceptions' string, which can disclose IPs/hosts.
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(timeout)
            kind, _, _, greeting = _frame(conn, limit=4096)
            if kind != 3:
                raise ShadNetProtocolError("server sent no shadNet greeting")
            head = struct.pack("<BHIQ", kind, 0, HEADER_BYTES + len(greeting), 0)
            parse_greeting(head, greeting)
            conn.sendall(pkt)
            for _ in range(8):
                kind, command, req_id, body = _frame(conn)
                if kind == 1 and command == 0 and req_id == 1:
                    return _login_result_payload(body)
            raise ShadNetProtocolError("no matching Login reply from server")
    except (socket.timeout, TimeoutError):
        return AuthResult(False, "Server timed out")
    except socket.gaierror:
        return AuthResult(False, "Server DNS lookup failed")
    except (OSError, ConnectionError):
        return AuthResult(False, "Cannot connect or the server closed the connection")
    except ShadNetProtocolError:
        return AuthResult(False, "Unexpected shadNet response or protocol mismatch")
