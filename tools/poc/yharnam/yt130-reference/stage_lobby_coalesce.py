#!/usr/bin/env python3
"""EXPERIMENT ONLY: coalesce non-hosted lobby broadcasts until Qt world Tick.

With 100/200 synthetic peers, authenticated YT1.3 lobby changes generate >60k
state messages and a reliable resend storm. OnWorldTick is already 50 ms:
batch all unrelated team edits instead of fanning out for EACH Settle call.
Newcomer OnLobbyHello sends its own initial state immediately; TeamStart and
reject notices are separately sent synchronously and unchanged. Hosted already
uses deferred Tick; keep original hosted interval unchanged.
Source-pinned, disposable server only, no prod/network-protocol change.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "server/src/bloodborne_world.cpp"
BLOB = "eca8c30d6fb78099b0f64a52388fd7d65f926e19"

OLD = """    if (outcome.changed) {
        if (hosted.enabled) {
            lobby_changed = true; // hosted: with the others at the next tick past the interval
        } else {
            SendLobby(now_ms);
        }
    }
    for (const std::string& name : outcome.starts) {"""

NEW = """    if (outcome.changed) {
        // Both hosted and non-hosted states wait for the next 50 ms world
        // Tick, so multiple team changes get one consolidated snapshot per
        // player. Hosted keeps its existing lobby_interval_ms limiter.
        // OnLobbyHello still sends the arriving player's state immediately,
        // and TeamStart/refusals are still emitted in this Result.
        lobby_changed = true;
    }
    for (const std::string& name : outcome.starts) {"""

TICK = """    if (lobby_changed && (!hosted.enabled || now_ms - lobby_sent_ms >= hosted.lobby_interval_ms)) {
        SendLobby(now_ms);
    }"""
HELLO = """    if (arrived) {
        // Its state even when nothing changed for the others.
        bbcoop::Envelope envelope;
        *envelope.mutable_lobby_state() = lobby.StateFor(member.lobby);
        SendTo(member, envelope, now_ms);
    }"""
TEAM_START = """                *envelope.mutable_team_start() = start;
                SendTo(member, envelope, now_ms);"""


def patch_text(text: str) -> str:
    for label, needle in (("Settle", OLD), ("Tick", TICK),
                          ("OnLobbyHello", HELLO), ("TeamStart", TEAM_START)):
        if text.count(needle) != 1:
            raise ValueError("Unrecognized official YT1.3 source / " + label)
    if text.count(NEW) != 0:
        raise ValueError("Already patched; no writes")
    return text.replace(OLD, NEW)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong pinned YT1.3 checkout")
    if git(root, "rev-parse", "HEAD:" + FILE) != BLOB:
        raise ValueError("Wrong original world source blob")
    path = root / FILE
    text = path.read_text(encoding="utf-8")
    result = patch_text(text)
    path.write_text(result, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_LOBBY_COALESCE_50MS_SYNTHETIC_EXPERIMENT_ONLY")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_official_yt_checkout", type=Path)
    apply(p.parse_args().disposable_official_yt_checkout)
