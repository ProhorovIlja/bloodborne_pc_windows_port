#!/usr/bin/env python3
"""V135: repair mismatched time domains in the REAL composed native game UDP.

The original shadPS4/YT P2P transport needs CLOCK_MONOTONIC for local timers
(reconnect, testing artificial delay, silence). However SHG2 grants and SHY2
AEAD tickets expire at an authenticated Unix/system-clock timestamp.
The V71 native DirectSender and V106 SHY2 ingress previously passed the
monotonic P2PNowMs() to wall-clock offer expiry/crypto. Keep the monotonic
clock for original local timers, and use explicit epoch milliseconds only for
crypto authorization. Do not arm any direct peer or change original Protocol8.

Staged AFTER existing real SHY2 game recvfrom patch, NOT on an invented
transport. Fail closed on missing/duplicate source anchors.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

GAME = "emulator/src/core/libraries/network/p2p_sockets.cpp"
TAG = "SHYT-V135-NATIVE-AUTH-UTC-CLOCK"
BEFORE = """s64 P2PNowMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}"""
AFTER = BEFORE + """

// SHYT-V135-NATIVE-AUTH-UTC-CLOCK: SHG2 signed expires_ms and SHY2 AES-GCM
// tickets are Unix epoch times, NEVER steady_clock or machine-uptime times.
// Keep original steady clock for silence, retransmit and local timers.
s64 P2PAuthEpochMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::system_clock::now().time_since_epoch())
        .count();
}"""
DIRECT_BEFORE = """{dest_addr_nbo,dest_port_nbo},framed,P2PNowMs()) ==
                    SeamlessHunt::Hybrid::NativeTxStatus::DirectSubmitted;"""
DIRECT_AFTER = """{dest_addr_nbo,dest_port_nbo},framed,P2PAuthEpochMs()) ==
                    SeamlessHunt::Hybrid::NativeTxStatus::DirectSubmitted;"""
INGRESS_BEFORE = """verified = native_shy2_ingress.Receive(
                        {from.sin_addr.s_addr,from.sin_port},datagram,P2PNowMs());"""
INGRESS_AFTER = """verified = native_shy2_ingress.Receive(
                        {from.sin_addr.s_addr,from.sin_port},datagram,P2PAuthEpochMs());"""


def replace_one(source: str, before: str, after: str, what: str) -> str:
    if source.count(before) != 1:
        raise ValueError(f"V135 REAL original game source drift: {what}")
    return source.replace(before, after, 1)


def patch_game(source: str) -> str:
    if TAG in source:
        raise ValueError("V135 cannot be staged twice")
    required = (
        "SHYT-V71-NATIVE-DIRECT-TX",
        "SHYT-SHY2-AUTHENTICATED-INGRESS",
        "SHYT-SHY2-ENCRYPTED-GAME-UDP",
        "SHYT-V87-TRUSTED-SERVER-LINK",
        "SHYT-V92-ORIGINAL-SOCKET-SIGNED-PROBE",
    )
    for name in required:
        if name not in source:
            raise ValueError(f"V135 missing original-game secure prerequisite: {name}")
    source = replace_one(source, BEFORE, AFTER, "original monotonic function")
    source = replace_one(source, DIRECT_BEFORE, DIRECT_AFTER, "actual SendFrame Direct")
    source = replace_one(source, INGRESS_BEFORE, INGRESS_AFTER, "actual recvfrom SHY2")
    if source.count("P2PAuthEpochMs()") != 3:
        raise ValueError("V135 must authorize only two crypto paths by epoch")
    if source.count(BEFORE) != 1 or "P2PNowMs() < link_cut_until_ms" not in source:
        raise ValueError("V135 touched original elapsed-time timers")
    if "direct_egress.Arm(" in source or "native_shy2_ingress.Arm(" in source:
        raise ValueError("Unexpected unauthorized native game Direct arm")
    return source


def patch_disposable_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink() or path.name != "p2p_sockets.cpp":
        raise ValueError("Need existing disposable native P2PTransport C++ source")
    before = path.read_text(encoding="utf-8")
    after = patch_game(before)
    path.write_text(after, encoding="utf-8")
    print("SHYT_V135_REAL_NATIVE_GAME_AUTH_EPOCH_CLOCK_SOURCE_STAGED_DIRECT_OFF")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("composed_game_cpp", type=Path)
    patch_disposable_file(parser.parse_args().composed_game_cpp)
