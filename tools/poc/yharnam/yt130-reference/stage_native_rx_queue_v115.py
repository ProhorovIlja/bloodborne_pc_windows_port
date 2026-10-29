#!/usr/bin/env python3
"""V115: patch REAL Yharnam Together v1.3 P2PSocket RX memory bound.

Source-pinned original Protocol8 C++ game, no P2P behavior/sender auth changes.
Preserve readiness signals; cap only pathological unconsumed UDP backlogs.
Import the exact portable C++ policy header verified by native unit tests.
"""
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP = "emulator/src/core/libraries/network/p2p_sockets.cpp"
SOCKETS = "emulator/src/core/libraries/network/sockets.h"
HEADER = "emulator/src/core/libraries/network/net_rx_queue_limits_v115.h"
BLOBS = {
    CPP: "087aef46868b55320f139b3f7c4f46e5fc545347",
    SOCKETS: "5e4636ee0b4c67a849f8d45c6bf50e590f27c87e",
}
MARKER = "SHYT-V115-BOUNDED-NATIVE-UDP-RX-QUEUE"
IMPORT = '#include "core/libraries/network/net_rx_queue_limits_v115.h"'
ANCHOR_INCLUDE = '#include "core/libraries/network/net_delay.h"'
ANCHOR_MEMBER = "    std::deque<P2PDatagram> receive_queue;"
NEW_MEMBER = """    std::deque<P2PDatagram> receive_queue;
    // SHYT-V115-BOUNDED-NATIVE-UDP-RX-QUEUE:
    // Only under receive_mutex; the original readiness FD follows the
    // queue's empty/nonempty transition, not its number of datagrams.
    std::size_t receive_queued_bytes{0};
    std::size_t receive_dropped_packets{0};"""
ANCHOR_CONSUMED = """    if (!peek) {
        receive_queue.pop_front();"""
NEW_CONSUMED = """    if (!peek) {
        RxBudget::Consumed(receive_queue.front(), receive_queued_bytes);
        receive_queue.pop_front();"""
ANCHOR_PUSH = "    receive_queue.push_back(std::move(packet));"
NEW_PUSH = """    // SHYT-V115-BOUNDED-NATIVE-UDP-RX-QUEUE: unchanged until the title
    // falls behind by 4096 datagrams OR 8 MiB per P2P game socket.
    // Under actual saturation, prefer recent UDP to a growing backlog
    // of minutes-old frames (reliable game channels may retransmit).
    const auto inserted = RxBudget::Enqueue(receive_queue, receive_queued_bytes,
                                            std::move(packet));
    receive_dropped_packets += inserted.evicted + (inserted.accepted ? 0 : 1);
    if (inserted.evicted || !inserted.accepted) {
        if (receive_dropped_packets == 1 || receive_dropped_packets % 1024 == 0) {
            LOG_WARNING(Lib_Net,
                        "P2P RX queue overload: {} discarded datagrams; queued={} bytes={}; "
                        "transport loss is possible, not a latency PASS",
                        receive_dropped_packets, receive_queue.size(), receive_queued_bytes);
        }
    }
    if (!inserted.accepted)
        return; // no readiness signal for rejected oversized packet"""

def one(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{MARKER} exact original C++ anchor drift {label}: {count}")
    return source.replace(old, new, 1)

def rewrite(cpp: str, sockets: str, helper: str) -> tuple[str, str, str]:
    if MARKER in cpp or MARKER in sockets or IMPORT in cpp:
        raise ValueError(f"{MARKER} repeated staging denied")
    if "namespace Libraries::Net::RxBudget {" not in helper or "MaxPayloadBytes" not in helper:
        raise ValueError("V115 native helper missing policy")
    cpp = one(cpp, ANCHOR_INCLUDE, ANCHOR_INCLUDE + "\n" + IMPORT, "include")
    cpp = one(cpp, ANCHOR_CONSUMED, NEW_CONSUMED, "peek/pop consumption")
    cpp = one(cpp, ANCHOR_PUSH, NEW_PUSH, "UDP EnqueuePacket")
    sockets = one(sockets, ANCHOR_MEMBER, NEW_MEMBER, "bounded socket fields")
    return cpp, sockets, helper

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("V115 refuses alternate game/source version")
    for rel, blob in BLOBS.items():
        p = root / rel
        if not p.is_file() or p.is_symlink():
            raise ValueError("V115 missing/linked source " + rel)
        if git(root, "rev-parse", "HEAD:" + rel) != blob:
            raise ValueError("V115 wrong original blob " + rel)
        if git(root, "diff", "--", rel):
            raise ValueError("V115 game socket source already modified: " + rel)
    helper_path = Path(__file__).resolve().parent / "native/net_rx_queue_limits_v115.h"
    target = root / HEADER
    if not helper_path.is_file() or helper_path.is_symlink() or target.exists() or target.is_symlink():
        raise ValueError("V115 unsafe original native helper path")
    cpp, sock, helper = rewrite((root / CPP).read_text(encoding="utf-8"),
                                (root / SOCKETS).read_text(encoding="utf-8"),
                                helper_path.read_text(encoding="utf-8"))
    (root / CPP).write_text(cpp, encoding="utf-8")
    (root / SOCKETS).write_text(sock, encoding="utf-8")
    target.write_text(helper, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("SHYT_V115_REAL_NATIVE_GAME_SOCKET_QUEUE_BOUNDED_NOT_A_LIVE_TEST")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_native_rx_queue_v115.py PINNED_ORIGINAL_YT13")
    stage(Path(sys.argv[1]))
