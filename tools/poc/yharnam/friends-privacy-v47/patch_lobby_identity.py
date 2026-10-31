#!/usr/bin/env python3
"""Bind native game lobby and world member IDs to the authenticated UDP link ID.

The game uses lowercase hex(online ID) in both Hello.member and LobbyHello.member.
The signed-in account arrives separately in Service::Receive. Never trust the
client's member string or its character display name to establish identity.
"""
from __future__ import annotations

WORLD = "server/src/bloodborne_world.cpp"
WORLD_H = "server/src/bloodborne_world.h"
LINK = "server/src/link_server.cpp"
HEADER = "server/src/sh_lobby_identity.hpp"

def once(src: str, before: str, after: str, label: str) -> str:
    if src.count(before) != 1:
        raise ValueError("V48 authentication anchor drifted: " + label)
    return src.replace(before, after, 1)

CHECK = """SeamlessHunt::Identity::MatchesAuthenticatedMember(
                std::string_view(member.online_id.constData(),
                                 static_cast<std::size_t>(member.online_id.size())),
                hello.member())"""

def transform(sources: dict[str, str]) -> dict[str, str]:
    if set(sources) != {WORLD, WORLD_H, LINK}:
        raise ValueError("V48 expects only Qt native world and link server files")
    world, header, link = (sources[k] for k in (WORLD, WORLD_H, LINK))
    if "SHYT-V48-LOBBY-ACCOUNT-BOUND" in world or "RequireAuthenticatedIdentity();" in link:
        raise ValueError("V48 already applied")
    world = once(world, '#include "bloodborne_world.h"\n',
                 '#include "bloodborne_world.h"\n#include "sh_lobby_identity.hpp"\n',
                 "world include")
    hello = """    // SHYT-V48-LOBBY-ACCOUNT-BOUND: a Coop/party Hello cannot
    // impersonate a different signed-in hunter via its member string.
    if (require_authenticated_identity && !""" + CHECK + """) {
        welcome.set_text("Co-op member does not match the authenticated account");
        SendTo(member, answer, now_ms);
        return;
    }
"""
    world = once(world, "    // The same run saying hello again", hello + "    // The same run saying hello again",
                 "party Hello authenticated identity")
    lobby = """    // SHYT-V48-LOBBY-ACCOUNT-BOUND: client-owned LobbyHello.member must
    // exactly equal the lowercase hex of ServerLink's authenticated account.
    // The character label (hello.name) is NOT an account credential.
    if (require_authenticated_identity && !""" + CHECK + """) {
        bbcoop::Envelope answer;
        answer.mutable_lobby_state()->set_notice(
            "Co-op lobby member does not match the authenticated account");
        SendTo(member, answer, now_ms);
        return;
    }
"""
    world = once(world, "    const bool arrived = member.lobby.empty();\n",
                 lobby + "    const bool arrived = member.lobby.empty();\n", "lobby Hello identity")
    header = once(header, "    const BloodborneCoop::TeamLobby& Lobby() const {\n",
                  "    // Enabled by LinkServer after opening the accounts DB; offline fixture\n"
                  "    // tests deliberately exercise the upstream unbound setup.\n"
                  "    void RequireAuthenticatedIdentity() { require_authenticated_identity = true; }\n"
                  "    const BloodborneCoop::TeamLobby& Lobby() const {\n", "server API")
    header = once(header, "    BloodborneCoop::TeamLobby lobby;\n",
                  "    bool require_authenticated_identity = false; // ALWAYS enabled by native LinkServer\n"
                  "    BloodborneCoop::TeamLobby lobby;\n", "server identity state")
    link = once(link,
                '    // Phase 11: the hello signs the player in (its id\'s account is made the first time).\n',
                '    // SHYT-V48-LOBBY-ACCOUNT-BOUND: production game sessions MUST bind\n'
                '    // lobby and world members to the account authenticated at ServerLink Hello.\n'
                '    m_world.RequireAuthenticatedIdentity();\n'
                '    // Phase 11: the hello signs the player in (its id\'s account is made the first time).\n',
                "production enablement")
    return {WORLD: world, WORLD_H: header, LINK: link}
