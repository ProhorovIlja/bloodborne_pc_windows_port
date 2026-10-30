#!/usr/bin/env python3
"""Source-pinned Qt YT1.3 experiment: coalesce GLOBAL lobby updates on burst joins.

Baseline native 64 simulated players: 3,452 LobbyState envelopes, 15.84 MB of
outgoing CoopStream vs 1.40 MB incoming, 546ms max Qt read callback, 114.747ms
relay p99. Earlier 50ms coalescing was NOT enough. This limits non-hosted
world broadcasts to once every 250 ms ONLY with >32 linked members.
Small lobbies retain the original 50ms refresh, and newcomers immediately get
their own OnLobbyHello state. TeamStart/refusals still send synchronously;
no protocol changes, information filters, extra account authority, P2P
enablement, dropped packets or Fornex changes.

The conditional is intentionally easy to remove if real Qt bbload QoS worsens.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = "server/src/bloodborne_world.cpp"
BLOB = "eca8c30d6fb78099b0f64a52388fd7d65f926e19"
STAGED_TICK = """    if (lobby_changed && (!hosted.enabled || now_ms - lobby_sent_ms >= hosted.lobby_interval_ms)) {
        SendLobby(now_ms);
    }"""
BATCH_TICK = """    // V128 EXPERIMENT: during >32 unhosted online members, batch burst
    // lobby discovery edits for up to 250ms. Tiny co-op groups retain the
    // original 50ms world refresh; hosted lobby interval is unchanged.
    // OnLobbyHello sends the arriving player's state IMMEDIATELY, and
    // TeamStart/refusals are synchronous from Settle (not delayed here).
    const qint64 nonhosted_lobby_wait_ms =
        !hosted.enabled && members.size() > 32 ? 250 : 0;
    if (lobby_changed &&
        (hosted.enabled ? now_ms - lobby_sent_ms >= hosted.lobby_interval_ms
                        : now_ms - lobby_sent_ms >= nonhosted_lobby_wait_ms)) {
        SendLobby(now_ms);
    }"""
HELLO = """    if (arrived) {
        // Its state even when nothing changed for the others.
        bbcoop::Envelope envelope;
        *envelope.mutable_lobby_state() = lobby.StateFor(member.lobby);
        SendTo(member, envelope, now_ms);
    }"""
START = """                *envelope.mutable_team_start() = start;
                SendTo(member, envelope, now_ms);"""


def rewrite(src: str) -> str:
    for label, needle in (
        ("original coalesced world Tick", STAGED_TICK),
        ("immediate newcomer state", HELLO),
        ("synchronous TeamStart", START),
    ):
        if src.count(needle) != 1:
            raise ValueError("YT1.3 source drift: " + label)
    if "V128 EXPERIMENT" in src:
        raise ValueError("Repeated V128 staging")
    if src.count("SendLobby(now_ms);") != 1:
        raise ValueError("Unexpected eager/bypass lobby broadcast still remains")
    return src.replace(STAGED_TICK, BATCH_TICK)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong pinned YT1.3 checkout")
    if git(root, "rev-parse", "HEAD:" + PATH) != BLOB:
        raise ValueError("Original pinned Bloodborne world blob changed")
    f = root / PATH
    f.write_bytes(rewrite(f.read_text(encoding="utf-8")).encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V128_BURST_LOBBY_250MS_ONLY_OVER_32_UNHOSTED_STAGED_NOT_CAPACITY")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_pinned_yt130_source", type=Path)
    apply(p.parse_args().disposable_pinned_yt130_source)
