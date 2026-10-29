#!/usr/bin/env python3
"""Fail closed if the *actual native* Bloodborne YT1.3 game and Qt server disagree.

The old native Windows v1.1.9 prototype uses Protocol 7. Target server 1.3
uses Protocol 8. They MUST NOT be packaged as a working joined pair.
Check both actual hello paths AND server refusal paths. A raw numeric edit
is not a compatibility upgrade: require all pinned client/control source
content and identical full protobuf schemas, not just matching '8'.

Run on original YT1.3 Git checkout AFTER current five-player source stages.
May also compare TWO distinct checkouts when making the Windows release.
No live server, user data, emulator or game assets.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path

TAG = "SHYT_YT130_AUTHENTIC_CLIENT_SERVER_PROTOCOL8"
PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CLIENT_SOURCE = "emulator/src/core/bloodborne_server_world.cpp"
COMMON_SOURCE = "server/coop/coop_messages.h"
PROTO_SOURCE = "server/coop/coop.proto"
SERVER_SOURCE = "server/src/bloodborne_world.cpp"
PIN_BLOBS = {
    CLIENT_SOURCE: "9bce9a73fe1d9956774be5d2b7559f34a4c4edf7",
    COMMON_SOURCE: "796d90d5bedb581c5d7b484c16c42ec308c54c9a",
    PROTO_SOURCE: "cd6147f9904998cb13c9a267d923f7147294542a",
}
C_HELLOS = (
    "hello.mutable_hello()->set_protocol(CoopProtocol);",
    "hello.mutable_lobby_hello()->set_protocol(CoopProtocol);",
)
S_DENIALS = (
    "if (hello.protocol() != CoopProtocol) {",
    "if (hello.protocol() != CoopProtocol || hello.member().empty()) {",
)
PROTO_PATTERN = re.compile(r"^\s*PROTOCOL_CURRENT\s*=\s*(\d+)\s*;", re.M)


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def check_text(client: str, common: str, proto: str, server: str) -> None:
    """Use exact checked original connection paths, never guess compatibility."""
    versions = PROTO_PATTERN.findall(proto)
    if versions != ["8"]:
        raise ValueError("YT1.3 Protocol 8 protobuf schema required, no 7/9 fallback")
    if "uint32 protocol = 1;" not in proto or proto.count(
        "uint32 protocol = 1;") < 2:
        raise ValueError("Both native Hello and LobbyHello need protocol field")
    if common.count("constexpr u32 CoopProtocol = bbcoop::PROTOCOL_CURRENT;") != 1:
        raise ValueError("Control channel no longer shares protobuf protocol enum")
    for anchor in C_HELLOS:
        if client.count(anchor) != 1:
            raise ValueError("Native game HELLO or LOBBY HELLO no longer authentic")
    for anchor in S_DENIALS:
        if server.count(anchor) != 1:
            raise ValueError("Server must refuse both incompatible game and lobby hellos")
    if server.count('"co-op protocol " + std::to_string(hello.protocol())') < 2:
        raise ValueError("Server's protocol refusal should explain wrong version")


def original(root: Path, name: str, pinned: bool) -> bytes:
    path = root / name
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing pinned original source: " + name)
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if pinned and name in PIN_BLOBS and blob(raw) != PIN_BLOBS[name]:
        raise ValueError("Original YT1.3 native protocol source blob drift: " + name)
    return raw


def check_pair(client_root: Path, server_root: Path, *, pinned: bool = True) -> None:
    roots = (client_root.resolve(strict=True), server_root.resolve(strict=True))
    if pinned:
        for root in set(roots):
            commit = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
                capture_output=True, check=True).stdout.strip()
            if commit != PIN:
                raise ValueError(f"Yharnam Together protocol pairing needs real 1.3 source {PIN}")
    game, server = roots
    game_proto = original(game, PROTO_SOURCE, pinned)
    server_proto = original(server, PROTO_SOURCE, pinned)
    if game_proto != server_proto:
        raise ValueError("Native game and Qt server protobuf schemas differ")
    texts = [original(game, CLIENT_SOURCE, pinned),
             original(game, COMMON_SOURCE, pinned), game_proto,
             original(server, SERVER_SOURCE, pinned)]
    check_text(*(x.decode("utf-8") for x in texts))
    print(TAG + " original two HELLO send paths and two refusal paths PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--server-root", type=Path, required=True)
    args = parser.parse_args()
    check_pair(args.client_root, args.server_root)


if __name__ == "__main__":
    main()
