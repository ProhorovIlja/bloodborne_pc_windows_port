#!/usr/bin/env python3
"""V116: prevent unbounded atomic RMW/log counter wrap in ACTUAL YT1.3 UDP game.

Run on pinned Protocol8 original game AFTER V115. Source-only change to the
per-client P2PSocket packet diagnostics: preserve the first 3000 long/short
packets as before, but stop modifying the atomic forever after saturation.
Not a direct P2P change and not a substitute for real game/Windows CI.
"""
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP = "emulator/src/core/libraries/network/p2p_sockets.cpp"
TARGET = "emulator/src/core/libraries/network/net_p2p_log_budget_v116.h"
V115_HEADER = "emulator/src/core/libraries/network/net_rx_queue_limits_v115.h"
PINNED_BLOB = "087aef46868b55320f139b3f7c4f46e5fc545347"
MARKER = "SHYT-V115-BOUNDED-NATIVE-UDP-RX-QUEUE"
IMPORT = '#include "core/libraries/network/net_p2p_log_budget_v116.h"'
INCLUDE_ANCHOR = '#include "core/libraries/network/net_firewall.h"'
ORIGINAL_FN = """bool LogsPacket(size_t size) {
    if (size >= LongPacket) {
        return long_packets_logged.fetch_add(1) < JoinPacketsLogged;
    }
    return join_packets_logged.fetch_add(1) < JoinPacketsLogged;
}"""
REPLACEMENT_FN = """bool LogsPacket(size_t size) {
    // V116: the first 3000 long/short diagnostic lines remain available.
    // Avoid an atomic write for EVERY game packet forever after that, and
    // never wrap the counter to zero to unexpectedly start logging again.
    if (size >= LongPacket) {
        return PacketLogBudget::Take(long_packets_logged, JoinPacketsLogged);
    }
    return PacketLogBudget::Take(join_packets_logged, JoinPacketsLogged);
}"""

def one(text: str, original: str, new: str, label: str) -> str:
    count = text.count(original)
    if count != 1:
        raise ValueError(f"V116 pinned original game source drift: {label} ({count})")
    return text.replace(original, new, 1)

def rewrite(cpp: str, helper: str) -> tuple[str, str]:
    if MARKER not in cpp:
        raise ValueError("V116 requires actual V115 bounded P2PSocket patch first")
    if IMPORT in cpp or "PacketLogBudget::Take" in cpp:
        raise ValueError("V116 already staged")
    if ("namespace Libraries::Net::PacketLogBudget {" not in helper or
            "compare_exchange_weak" not in helper):
        raise ValueError("V116 missing real atomic helper")
    cpp = one(cpp, INCLUDE_ANCHOR, INCLUDE_ANCHOR + "\n" + IMPORT, "include")
    return one(cpp, ORIGINAL_FN, REPLACEMENT_FN, "LogsPacket"), helper

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("V116 rejects non-pinned YT1.3 Protocol8 game")
    original = root / CPP
    previous = root / V115_HEADER
    target = root / TARGET
    helper_path = Path(__file__).resolve().parent / "native/net_p2p_log_budget_v116.h"
    if (not original.is_file() or original.is_symlink() or
            not previous.is_file() or previous.is_symlink() or
            not helper_path.is_file() or helper_path.is_symlink() or
            target.exists() or target.is_symlink()):
        raise ValueError("V116 original socket/helper stage unsafe or missing")
    if git(root, "rev-parse", "HEAD:" + CPP) != PINNED_BLOB:
        raise ValueError("V116 original game source blob mismatched")
    if not git(root, "diff", "--", CPP):
        raise ValueError("V116 original V115 game patch has not been staged")
    # Fail closed and validate both edits BEFORE touching any file.
    game_cpp, helper = rewrite(original.read_text(encoding="utf-8"),
                               helper_path.read_text(encoding="utf-8"))
    original.write_text(game_cpp, encoding="utf-8")
    target.write_text(helper, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V116_NATIVE_UDP_DIAGNOSTIC_ATOMICS_STAGED_NOT_A_GAME_BUILD_PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_native_p2p_log_v116.py PINNED_YT13_CLONE")
    stage(Path(sys.argv[1]))
