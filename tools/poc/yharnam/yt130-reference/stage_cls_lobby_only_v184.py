#!/usr/bin/env python3
"""V184: opt-in lobby-only caps from CLS 0.1.3, ported to pinned original YT1.3.

Do not enable Hosted authentication, ban/admin policy, world/name ownership,
account creation or packet rate limits. The original unhosted, no-cap default
remains identical. All edits are exact-anchor source gated and use only public
original Qt files, never retail game assets or private build binaries.

CLS donor provenance: 2026-10-31 private source archive; feature concept
LobbyLimits / independent lobby throttle. GPL source attribution remains.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
MARK = "SHYT_V184_CLS_INDEPENDENT_LOBBY_LIMITS"
PATCHES = {
    "server/src/config.h": (
        ("    bool stats = false;        // the stats page (it lists player ids; StatsEnabled as well)",
         "    // SHYT_V184_CLS_INDEPENDENT_LOBBY_LIMITS: opt-in on non-hosted servers.\n"
         "    bool lobbyLimits = false;\n"
         "    bool stats = false;        // the stats page (it lists player ids; StatsEnabled as well)"),
    ),
    "server/src/config.cpp": (
        ('    m_hosted.partyWorlds = str("HostedPartyWorlds", "2048").toInt();',
         '    m_hosted.partyWorlds = str("HostedPartyWorlds", "2048").toInt();\n'
         '    m_hosted.lobbyLimits = boolean("LobbyLimits", false);'),
    ),
    "server/src/bloodborne_world.h": (
        ("struct HostedRules {\n    bool enabled = false;\n    size_t lobby_players = 32;",
         "struct HostedRules {\n    bool enabled = false;\n"
         "    // Non-hosted: cap/throttle the lobby only, never change world ownership.\n"
         "    bool lobby_limits = false;\n    size_t lobby_players = 32;"),
        ("    HostedRules hosted;\n    Limits limits;",
         "    HostedRules hosted;\n"
         "    bool LobbyLimited() const {\n"
         "        return hosted.enabled || hosted.lobby_limits;\n"
         "    }\n"
         "    Limits limits;"),
    ),
    "server/src/bloodborne_world.cpp": (
        ("    if (lobby_changed && (!hosted.enabled || now_ms - lobby_sent_ms >= hosted.lobby_interval_ms)) {",
         "    if (lobby_changed && (!LobbyLimited() || now_ms - lobby_sent_ms >= hosted.lobby_interval_ms)) {"),
        ("            if (hosted.enabled) {\n"
         "                // Only to the players whose own state changed.",
         "            if (LobbyLimited()) {\n"
         "                // Only to the players whose own state changed."),
        ("void Service::SetHosted(const HostedRules& rules) {\n"
         "    hosted = rules;\n"
         "    if (rules.enabled) {\n"
         "        lobby.SetHosted(rules.lobby_players, rules.worlds_per_player);\n"
         "    }\n}",
         "void Service::SetHosted(const HostedRules& rules) {\n"
         "    hosted = rules;\n"
         "    if (rules.enabled) {\n"
         "        lobby.SetHosted(rules.lobby_players, rules.worlds_per_player);\n"
         "    } else if (rules.lobby_limits) {\n"
         "        lobby.SetLobbyCap(rules.lobby_players);\n"
         "    }\n}"),
    ),
    "server/coop/team_lobby.h": (
        ("    bool Hosted() const {\n        return hosted;\n    }",
         "    // SHYT_V184_CLS_INDEPENDENT_LOBBY_LIMITS: keep worlds visible.\n"
         "    void SetLobbyCap(size_t limit) {\n"
         "        capped = true;\n"
         "        lobby_players = limit;\n"
         "    }\n"
         "    bool Hosted() const {\n        return hosted;\n    }"),
        ("    size_t lobby_players = 0;\n    size_t worlds_per_player = 0;",
         "    size_t lobby_players = 0;\n"
         "    bool capped = false;\n"
         "    size_t worlds_per_player = 0;"),
    ),
    "server/coop/team_lobby.cpp": (
        ("    if (!hosted) {\n"
         "        for (const auto& [other, player] : players) {\n"
         "            if (other != member) {\n"
         "                add_player(other, player);",
         "    if (!hosted && !capped) {\n"
         "        for (const auto& [other, player] : players) {\n"
         "            if (other != member) {\n"
         "                add_player(other, player);"),
    ),
    "server/src/link_server.cpp": (
        ("    }\n    if (shared && shared->config) {\n"
         "        const InvasionConfig invasions = shared->config->GetInvasions();",
         "    } else if (m_hosted.lobbyLimits) {\n"
         "        // Independent from Hosted: do not enable hosted-only identity,\n"
         "        // login, admin, throttling of packets or world ownership.\n"
         "        BloodborneWorld::HostedRules rules;\n"
         "        rules.lobby_limits = true;\n"
         "        rules.lobby_players = static_cast<size_t>(std::max(0, m_hosted.lobbyPlayers));\n"
         "        rules.lobby_interval_ms = m_hosted.lobbyIntervalMs;\n"
         "        m_world.SetHosted(rules);\n"
         "        qInfo().noquote() << QStringLiteral("
         '"Lobby-only limits enabled: %1 other players, %2 ms minimum")\n'
         "                                 .arg(rules.lobby_players)\n"
         "                                 .arg(rules.lobby_interval_ms);\n"
         "    }\n    if (shared && shared->config) {\n"
         "        const InvasionConfig invasions = shared->config->GetInvasions();"),
    ),
}

def rewrite(path: str, source: str) -> str:
    if path not in PATCHES:
        raise ValueError("V184 unexpected source path")
    for old, new in PATCHES[path]:
        if source.count(old) != 1 or new in source:
            raise ValueError("V184 pinned original Qt anchor drift: " + path)
        source = source.replace(old, new, 1)
    return source

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                               text=True, stderr=subprocess.DEVNULL).strip() != PIN:
        raise ValueError("V184 requires exact disposable original YT1.3 checkout")
    changed = {}
    # All seven files are checked BEFORE the first write, no partial source drift.
    for name in PATCHES:
        file = root / name
        if not file.is_file() or file.is_symlink():
            raise ValueError("V184 requires regular pinned original Qt file: " + name)
        changed[file] = rewrite(name, file.read_text(encoding="utf-8"))
    for file, source in changed.items():
        file.write_text(source, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_V184_CLS_LOBBY_ONLY_CAP_STAGED_DISABLED_BY_DEFAULT_NO_HOSTED")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_cls_lobby_only_v184.py PINNED_DISPOSABLE_YT130")
    stage(Path(sys.argv[1]))
