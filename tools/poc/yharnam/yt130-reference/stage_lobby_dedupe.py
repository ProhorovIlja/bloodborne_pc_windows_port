#!/usr/bin/env python3
"""EXPERIMENT ONLY: deduplicate unchanged lobby states on non-hosted YT1.3 servers.

The official v1.3 server already performs byte-identical lobby-state dedupe in
Hosted mode. The non-hosted path needlessly resends unchanged reliable states
to every other linked member for every team edit. This patch makes the existing
dedupe common to both paths, with no changes to wire protocol or user accounts.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
RELATIVE = "server/src/bloodborne_world.cpp"
ORIGINAL_BLOB = "eca8c30d6fb78099b0f64a52388fd7d65f926e19"

BEFORE = """            if (hosted.enabled) {
                // Only to the players whose own state changed.
                std::string bytes = envelope.lobby_state().SerializeAsString();
                std::string& sent = lobby_sent[member.lobby];
                if (sent == bytes) {
                    continue;
                }
                sent = std::move(bytes);
            }
            SendTo(member, envelope, now_ms);"""

AFTER = """            // A lobby-state envelope is delivered by CoopStream with ACKs
            // and resends. Do not resend an identical one just because an
            // unrelated team changed, even when Hosted is disabled.
            // Each new lobby hello separately receives its initial state.
            std::string bytes = envelope.lobby_state().SerializeAsString();
            std::string& sent = lobby_sent[member.lobby];
            if (sent == bytes) {
                continue;
            }
            sent = std::move(bytes);
            SendTo(member, envelope, now_ms);"""


def patch_text(source: str) -> str:
    if source.count(BEFORE) != 1:
        raise ValueError("Source drift or duplicate SendLobby; no changes")
    if source.count("void Service::SendLobby(qint64 now_ms)") != 1:
        raise ValueError("Missing or ambiguous target function; no changes")
    if source.count("void Service::OnLobbyHello(") != 1:
        raise ValueError("Cannot verify guaranteed first state on reconnect")
    if "A lobby-state envelope is delivered by CoopStream" in source:
        raise ValueError("Already patched; refuse repeated staging")
    return source.replace(BEFORE, AFTER)


def git_read(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git_read(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong upstream revision; no writes")
    if git_read(root, "rev-parse", "HEAD:" + RELATIVE) != ORIGINAL_BLOB:
        raise ValueError("Wrong upstream byte-exact source; no writes")
    path = root / RELATIVE
    if not path.is_file():
        raise ValueError("Missing server world implementation; no writes")
    before = path.read_text(encoding="utf-8")
    changed = patch_text(before)
    path.write_text(changed, encoding="utf-8")
    print("YT130_NONHOSTED_LOBBY_DEDUP_EXPERIMENT_APPLIED_TO_DISPOSABLE_SRC")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_upstream_checkout", type=Path)
    apply(parser.parse_args().disposable_upstream_checkout)
