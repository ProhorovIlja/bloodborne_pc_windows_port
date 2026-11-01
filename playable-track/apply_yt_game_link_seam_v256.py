#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V256: source-locked, fail-closed integration with the REAL YT 1.3.1
RunGamePacketLink transmit loop. Default mode CHECK makes no changes.
Apply only to a separate cloned upstream SOURCE checkout, not live Fornex.
Direct P2P intentionally DISABLED until independently verified server
grants, direct key/endpoint and receive path are wired into the runtime.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PINNED_UPSTREAM = "5d2305ee611ef1e03be39ff925f0da75c9a70393"
PINNED_BLOODBORNE_PATCHES_BLOB = "5e698a5bcd714f41ab40782a0838d63055d84d62"
UPSTREAM_PATH = "emulator/src/core/bloodborne_patches.cpp"
HEADERS = (
    "hybrid_transport_policy_v1.h",
    "hybrid_direct_ingress_v2.h",
    "hybrid_direct_egress_v240.h",
    "hybrid_direct_ack_coalescer_v251.h",
    "hybrid_peer_crypto_v241.h",
    "yt_game_link_runtime_bridge_v255.h",
)
INCLUDE_POINT = '#include "core/bloodborne_game_link.h"'
NEW_INCLUDE = '#include "core/shyt_hybrid/yt_game_link_runtime_bridge_v255.h"'
ORIGINAL_QUEUE = (
    "std::vector<std::pair<std::pair<u32, u16>, std::vector<u8>>> out;"
)
REPLACEMENT_QUEUE = "std::vector<BloodborneCoop::SHYTHybrid::PendingYtFrameV255> out;"
ORIGINAL_FRAME_LOOP = """                for (const GameFrame& frame : peer.Flush(now_ms)) {
                    std::vector<u8> bytes{'S', 'H', 'A', 'D', GamePacketsType};
                    const auto payload = EncodeGameFrame(frame);
                    bytes.insert(bytes.end(), payload.begin(), payload.end());
                    out.emplace_back(address->second, std::move(bytes));
                }"""
REPLACEMENT_FRAME_LOOP = """                for (GameFrame& frame : peer.Flush(now_ms)) {
                    // Preserve original YT sequence/ACK; move, do not COPY,
                    // the (potentially large) GameFrame out of the lock.
                    // All socket I/O happens after game_link.mutex unlocks.
                    out.push_back({member, address->second, std::move(frame)});
                }"""
ORIGINAL_SEND = """        for (const auto& [address, bytes] : out) {
            Libraries::Net::P2PCoopSendTo(bytes.data(), static_cast<u32>(bytes.size()),
                                          address.first, address.second);
        }"""
REPLACEMENT_SEND = """        for (const auto& queued : out) {
            // V256: same source-level hook for all upstream GameLink frames.
            // The null trusted route means ORIGINAL authenticated shadNet
            // server transport, with the exact original SHAD wire envelope.
            // Never pass a fabricated lease or trust a bare UDP endpoint.
            BloodborneCoop::SHYTHybrid::DispatchYtFrameV255(
                queued, nullptr,
                [](const std::pair<u32, u16>& address, std::span<const u8> bytes) {
                    return Libraries::Net::P2PCoopSendTo(
                        bytes.data(), static_cast<u32>(bytes.size()),
                        address.first, address.second) >= 0;
                },
                [](std::string_view, std::span<const u8>) { return false; });
        }"""


def git(root: Path, *args: str) -> str:
    run = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        check=False, timeout=12,
    )
    if run.returncode != 0:
        raise ValueError("source must be a valid pinned Git checkout")
    return run.stdout.strip()


def pinned_path(root: Path) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("upstream checkout is absent or linked")
    if git(root, "rev-parse", "HEAD") != PINNED_UPSTREAM:
        raise ValueError("upstream commit drift; no blind game source patch")
    original = root / UPSTREAM_PATH
    if original.is_symlink() or not original.is_file():
        raise ValueError("missing or linked original game source")
    if git(root, "hash-object", UPSTREAM_PATH) != PINNED_BLOODBORNE_PATCHES_BLOB:
        raise ValueError("original YT game send/recv source differs")
    return original


def exact_replace(text: str, needle: str, repl: str) -> str:
    if text.count(needle) != 1:
        raise ValueError("upstream game-link anchor not unique: fail closed")
    return text.replace(needle, repl, 1)


def patch(text: str) -> str:
    result = exact_replace(text, INCLUDE_POINT, INCLUDE_POINT + "\n" + NEW_INCLUDE)
    result = exact_replace(result, ORIGINAL_QUEUE, REPLACEMENT_QUEUE)
    result = exact_replace(result, ORIGINAL_FRAME_LOOP, REPLACEMENT_FRAME_LOOP)
    result = exact_replace(result, ORIGINAL_SEND, REPLACEMENT_SEND)
    # The original received SHAD frames and single GameLinkPeer::Receive
    # handler are unchanged. Do NOT route direct frames into this code until
    # a verified separate UDP ingress callback has been installed.
    return result


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout", type=Path, required=True)
    p.add_argument("--mode", choices=("check","apply"), default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    source=pinned_path(root)
    existing=source.read_text(encoding="utf-8")
    candidate=patch(existing)
    if args.mode=="check":
        print("SHYT_V256_PINNED_YT_REAL_GAME_LINK_SOURCE_SEAM_CHECK_PASS")
        return
    source_dir=Path(__file__).resolve().parent
    if source_dir==root or root in source_dir.parents:
        raise ValueError("refusing in-place modification of project source")
    dst_dir=root/"emulator/src/core/shyt_hybrid"
    if dst_dir.exists() or dst_dir.is_symlink():
        raise ValueError("no overwrite/re-apply of existing hybrid adapter")
    sources=[]
    for name in HEADERS:
        src=source_dir/name
        if src.is_symlink() or not src.is_file() or src.stat().st_size>20000:
            raise ValueError("missing or unsafe bridge header")
        sources.append((name,src.read_bytes()))
    dst_dir.mkdir()
    for name,data in sources:
        (dst_dir/name).write_bytes(data)
    source.write_text(candidate,encoding="utf-8")
    print("SHYT_V256_PINNED_YT_SOURCE_SEND_SEAM_APPLIED_SERVER_FALLBACK_DEFAULT")


if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SystemExit("V256 refused unsafe/source-drift state: "+type(exc).__name__) from None
