#!/usr/bin/env python3
"""Source-verified, isolated FIVE-hunter synthetic load generator extension.

Extends original pinned bbload CLI to five, and ports upstream PR #444 multi-owner synthetic traffic.
Does not add server capacity, enable gameplay, or modify live binaries.
Original upstream 1.3 bbload would silently clamp requests for five to four.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

SOURCE = Path("server/loadtest/bbload.cpp")
PINNED_BLOB = "edfb6ea39b898cca2638d65826981cf9fc81c334"
OLD_HELP = '"team-size", "players a team (2-4)"'
NEW_HELP = '"team-size", "players a team (2-5)"'
OLD_CLAMP = 'std::clamp(parser.value("team-size").toInt(), 2, 4)'
NEW_CLAMP = 'std::clamp(parser.value("team-size").toInt(), 2, 5)'

# Source-reviewed port of original upstream PR #444 (lKaniel/bloodborne-server).
# The original generator models ONE enemy owner per team; since 1.3 a
# separated four-/five-hunter group may have several actual enemy owners.
# This affects load evidence ONLY, never game or server routing.
OWNER_EDITS = (
    ("  int follower_fps = 8; // a follower's\n",
     "  int follower_fps = 8; // a follower's\n  int owners = 1; // enemy owners in each team (upstream PR444)\n"),
    ("  bool Leader() const { return seat == 0; }\n",
     "  bool Leader() const { return seat == 0; }\n  bool Owner() const;\n"),
    ("bool Game::Elsewhere() const {",
     "bool Game::Owner() const { return seat < load.settings.owners; }\n\nbool Game::Elsewhere() const {"),
    ("Leader() ? load.settings.owner_fps : load.settings.follower_fps",
     "Owner() ? load.settings.owner_fps : load.settings.follower_fps"),
    ("    if (Leader()) {\n      // The enemy owner (rig 2026-10-15):",
     "    if (Owner()) {\n      // The enemy owner (rig 2026-10-15):"),
    ("      {\"follower-fps\", \"a follower's frames a second per teammate\", \"n\", \"8\"},",
     "      {\"follower-fps\", \"a follower's frames a second per teammate\", \"n\", \"8\"},\n      {\"owners\", \"enemy-owner seats per team (1-team size)\", \"n\", \"1\"},"),
    ("  settings.follower_fps = std::max(1, parser.value(\"follower-fps\").toInt());",
     "  settings.follower_fps = std::max(1, parser.value(\"follower-fps\").toInt());\n  settings.owners = std::clamp(parser.value(\"owners\").toInt(), 1, settings.team_size);"),
)


# Real per-client packet receipt is not implied by aggregate relay totals.
# Instrument only the pinned disposable bbload generator used in CI.
RECEIVER_EDITS = (
    ('  bool Linked() const { return state != State::Linking; }\n',
     '  bool Linked() const { return state != State::Linking; }\n'
     '  bool SawGamePackets() const { return received_game_packets != 0; }\n'),
    ('  u32 frame_count = 0;\n',
     '  u32 frame_count = 0;\n  quint64 received_game_packets = 0;\n'),
    ('    Report(NowUs());\n    int linked = 0;\n    int playing = 0;\n'
     '    for (auto &game : games) {\n      linked += game->Linked();\n'
     '      playing += game->Playing();\n    }',
     '    Report(NowUs());\n    int linked = 0;\n    int playing = 0;\n'
     '    int game_receivers = 0;\n'
     '    for (auto &game : games) {\n      linked += game->Linked();\n'
     '      playing += game->Playing();\n'
     '      game_receivers += game->Playing() && game->SawGamePackets();\n    }'),
    ('        {"playing", playing},\n        {"seconds", seconds},',
     '        {"playing", playing},\n        {"game_receivers", game_receivers},\n'
     '        {"seconds", seconds},'),
    ('    ++load.totals.packets_received;\n',
     '    ++load.totals.packets_received;\n    ++received_game_packets;\n'),
)

# V118: "PLAYING" and one received packet do not demonstrate forty complete
# five-hunter teams. Count original bbload leaders seeing all five members.
# This is a synthetic-test measurement only, never modifies server decisions.
FULL_TEAM_EDITS = (
    ("  bool SawGamePackets() const { return received_game_packets != 0; }\n",
     "  bool SawGamePackets() const { return received_game_packets != 0; }\n"
     "  bool CompleteTeam(int expected) const {\n"
     "    return seat == 0 && state == State::Playing && team_members == expected;\n"
     "  }\n"),
    ("    int game_receivers = 0;\n",
     "    int game_receivers = 0;\n    int complete_teams = 0;\n"),
    ("      game_receivers += game->Playing() && game->SawGamePackets();\n",
     "      game_receivers += game->Playing() && game->SawGamePackets();\n"
     "      complete_teams += game->CompleteTeam(settings.team_size);\n"),
    ('        {"game_receivers", game_receivers},\n',
     '        {"game_receivers", game_receivers},\n'
     '        {"complete_teams", complete_teams},\n'),
)

def patch_complete_teams(text: str) -> str:
    # Test the source-drift guards separately on the verified output of
    # the prior receiver instrumentation.
    for old, replacement in FULL_TEAM_EDITS:
        if text.count(old) != 1:
            raise ValueError("Pinned complete-five-team bbload anchor drift")
        text = text.replace(old, replacement, 1)
    return text



# V120: measure actual game payloads generated AFTER each load worker has
# every hunter Playing AND every leader has its exact five-member team. Each
# decoded entry carries its send timestamp, so late arrivals from the previous
# (joining/redirect) period are excluded rather than inflating delivery.
# IMPORTANT: instrumentation of the genuine upstream Qt bbload only.
STEADY_EDITS = (
    ('  quint64 packets_lost = 0; // gaps in the sequence numbers\n',
     '  quint64 packets_lost = 0; // gaps in the sequence numbers\n'
     '  quint64 steady_packets_sent = 0;\n'
     '  quint64 steady_packets_received = 0;\n'),
    ('  s64 started_us = 0;\n',
     '  s64 started_us = 0;\n'
     '  s64 steady_since_us = 0; // set once, after real full-team Playing\n'),
    ('    const double seconds = (now_us - last_report_us) / 1e6;\n',
     '    // V120: only real original whole-five team Playing can arm.\n'
     '    if (steady_since_us == 0 && playing == static_cast<int>(games.size())) {\n'
     '      int complete = 0;\n'
     '      for (auto &game : games) {\n'
     '        complete += game->CompleteTeam(settings.team_size);\n'
     '      }\n'
     '      if (complete == settings.teams) {\n'
     '        steady_since_us = now_us;\n'
     '      }\n'
     '    }\n'
     '    const double seconds = (now_us - last_report_us) / 1e6;\n'),
    ('        {"complete_teams", complete_teams},\n',
     '        {"complete_teams", complete_teams},\n'
     '        {"steady_packets_sent", static_cast<double>(totals.steady_packets_sent)},\n'
     '        {"steady_packets_received", static_cast<double>(totals.steady_packets_received)},\n'
     '        {"steady_window_ms", steady_since_us ?\n'
     '            static_cast<double>((NowUs() - steady_since_us) / 1000) : 0.0},\n'),
    ('    load.totals.packets_sent += frame.entries.size();\n',
     '    load.totals.packets_sent += frame.entries.size();\n'
     '    if (load.steady_since_us > 0 && now_us >= load.steady_since_us) {\n'
     '      load.totals.steady_packets_sent += frame.entries.size();\n'
     '    }\n'),
    ('    ++received_game_packets;\n',
     '    ++received_game_packets;\n'
     '    if (load.steady_since_us > 0 &&\n'
     '        static_cast<s64>(sent) >= load.steady_since_us) {\n'
     '      ++load.totals.steady_packets_received;\n'
     '    }\n'),
)


def patch_steady_window(text: str) -> str:
    for old, replacement in STEADY_EDITS:
        if text.count(old) != 1:
            raise ValueError("Pinned steady five-hunter game payload anchor drift")
        text = text.replace(old, replacement, 1)
    return text

def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\x00" + raw
    ).hexdigest()


def rewrite(text: str) -> str:
    for old in (OLD_HELP, OLD_CLAMP):
        if text.count(old) != 1:
            raise ValueError("Pinned five-player bbload source anchor drift")
    text = text.replace(OLD_HELP, NEW_HELP, 1).replace(
        OLD_CLAMP, NEW_CLAMP, 1
    )
    for old, new in OWNER_EDITS:
        if text.count(old) != 1:
            raise ValueError("Pinned upstream multi-owner bbload anchor drift")
        text = text.replace(old, new, 1)
    for old, replacement in RECEIVER_EDITS:
        if text.count(old) != 1:
            raise ValueError("Pinned game-receiver bbload anchor drift")
        text = text.replace(old, replacement, 1)
    return patch_steady_window(patch_complete_teams(text))


def transform(raw: bytes) -> bytes:
    if blob_sha(raw) != PINNED_BLOB:
        raise ValueError("Not exact official pinned upstream bbload.cpp")
    return rewrite(raw.decode("utf-8")).encode("utf-8")


def stage(root: Path) -> None:
    source = root.resolve() / SOURCE
    if not source.is_file() or source.is_symlink():
        raise ValueError("No safe regular disposable bbload source")
    source.write_bytes(transform(source.read_bytes()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_five_player_bbload.py DISPOSABLE_UPSTREAM")
    stage(Path(sys.argv[1]))
    print("SHYT_FIVE_HUNTER_BBLOAD_DIAGNOSTIC_ONLY_NO_SERVER_CAPACITY_CLAIM")
