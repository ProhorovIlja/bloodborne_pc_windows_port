#!/usr/bin/env python3
"""SHY2 authenticated encryption demux: fail closed until real authorized Arm.

The game's ORIGINAL recvfrom socket already demultiplexes SHP1 in V70.
An unarmed SHY2 datagram must NEVER enter the original relay/Link path, even
if it comes from a source impersonating the server endpoint. This patch does
not enable SHY2 game data or change other packet decoding or retransmits.
"""
from __future__ import annotations

NETWORK = "emulator/src/core/libraries/network/p2p_sockets.cpp"
AEAD_HEADER = "emulator/src/core/libraries/network/sh_native_game_aead.hpp"
TAG = "SHYT-SHY2-UNARMED-DROP"


def patch_game(src: str) -> str:
    if TAG in src:
        raise ValueError("SHY2 native demux already installed")
    if "SHYT-V70-NATIVE-RECV-HMAC" not in src:
        raise ValueError("SHY2 demux requires original V70 physical receive socket")
    marker = """            if (SeamlessHunt::Hybrid::IsSHP1(datagram)) {
                SeamlessHunt::Hybrid::NativeRxResult verified{};"""
    count = src.count(marker)
    if count != 1:
        raise ValueError(f"SHY2 pinned physical recvfrom anchor drift: {count}")
    # A future SHY2 receiver must replace ONLY this branch with server-verified
    # AEAD decryption + physical-candidate, team/world, and virtual-sender checks.
    # A four-byte magic byte sequence alone is NEVER gameplay authorization.
    guard = """            // SHYT-SHY2-UNARMED-DROP: encrypted Direct v2 is not yet
            // authorized by the native game's secure rendezvous installer.
            // An attacker-controlled datagram must never be forwarded to
            // legacy shadNet or the virtual game socket.
            if (datagram.size() >= 4 && datagram[0] == 'S' &&
                datagram[1] == 'H' && datagram[2] == 'Y' &&
                datagram[3] == '2') {
                continue;
            }
"""
    return src.replace(marker, guard + marker, 1)
