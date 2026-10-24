"""Strict parser for the BBSC/shadNet TCP protocol v1 *ServerInfo* greeting.

Wire layout from CLSAMG22/BBSC emulator/src/shadnet/client.h, client.cpp:
    packet_type:u8, command:u16le, total_size:u32le, packet_id:u64le
ServerInfo (type 3) begins with protocol_version:u32le.

This module never sends packets, performs account login or joins a party.
A successful greeting establishes that a compatible shadNet server answered
on TCP; it does NOT establish BBSC game compatibility or P2P connectivity.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

HEADER_BYTES = 15
SERVER_INFO = 3
EXPECTED_VERSION = 1
MAX_SERVER_INFO_BYTES = 4096


@dataclass(frozen=True)
class Greeting:
    version: int
    packet_id: int
    command: int


class ShadNetProtocolError(ValueError):
    pass


def parse_header(data: bytes) -> tuple[int, int, int, int]:
    if len(data) != HEADER_BYTES:
        raise ShadNetProtocolError("incomplete shadNet packet header")
    packet_type, cmd, total, packet_id = struct.unpack("<BH IQ".replace(" ", ""), data)
    if total < HEADER_BYTES or total > MAX_SERVER_INFO_BYTES:
        raise ShadNetProtocolError("invalid or excessive shadNet greeting length")
    if packet_type != SERVER_INFO:
        raise ShadNetProtocolError("peer is not sending shadNet ServerInfo")
    return packet_type, cmd, total, packet_id


def parse_greeting(header: bytes, payload: bytes) -> Greeting:
    _, cmd, total, packet_id = parse_header(header)
    if len(payload) != total - HEADER_BYTES or len(payload) < 4:
        raise ShadNetProtocolError("missing shadNet protocol version")
    version = struct.unpack_from("<I", payload, 0)[0]
    if version != EXPECTED_VERSION:
        raise ShadNetProtocolError("unsupported shadNet wire protocol version")
    return Greeting(version, packet_id, cmd)
