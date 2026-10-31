#!/usr/bin/env python3
"""V49: native in-game filter for authenticated mutual friends online.

No parallel accounts, token forwarding, new JOIN bypass, P2P disclosure or
unsolicited invasions. Only decorate existing team-lobby peers when the Qt
account DB confirms a mutual friendship and the friend has not blocked the
caller or hidden their presence. Existing INVITE remains the sole action.
"""
PROTO="server/coop/coop.proto"
WORLD="server/src/bloodborne_world.cpp"
WORLD_H="server/src/bloodborne_world.h"
LINK="server/src/link_server.cpp"
API="bbport/gpu/bbcoop.h"
IMPL="bbport/gpu/bbcoop/coop.cpp"
UI="bbport/gpu/shim/bbport_overlay.cpp"
PATHS={PROTO,WORLD,WORLD_H,LINK,API,IMPL,UI}
MARKER="SHYT-V49-ONLINE-MUTUAL-FRIENDS"

def once(s,old,new,label):
    if s.count(old)!=1:
        raise ValueError("V49 pinned source drift: "+label)
    return s.replace(old,new,1)

def transform(sources):
    if set(sources)!=PATHS:
        raise ValueError("V49 unexpected source collection")
    proto,world,header,link,api,impl,ui=(sources[k] for k in (PROTO,WORLD,WORLD_H,LINK,API,IMPL,UI))
    if MARKER in world or "mutual_friend = 12;" in proto:
        raise ValueError("V49 already applied")
    proto=once(proto,
        "    string team = 4; // the team it is in, if any\n",
        "    string team = 4; // the team it is in, if any\n"
        "    bool mutual_friend = 12; // server-computed, recipient-only; never supplied by the game\n",
        "proto mutual relationship field")
    header=once(header,"#include <map>\n","#include <functional>\n#include <map>\n","header functional")
    header=once(header,"#include <QList>\n","#include <QList>\n#include <QSet>\n","header friend ids")
    header=once(header,
        "    void RequireAuthenticatedIdentity() { require_authenticated_identity = true; }\n",
        "    void RequireAuthenticatedIdentity() { require_authenticated_identity = true; }\n"
        "    // Server-owned mutual friendship resolver; game supplied labels are never trusted.\n"
        "    void SetVisibleFriends(std::function<QSet<QByteArray>(const QByteArray&)> lookup) {\n"
        "        visible_friends = std::move(lookup);\n"
        "    }\n",
        "world social resolver API")
    header=once(header,"    void SendLobby(qint64 now_ms);\n",
        "    bbcoop::LobbyState LobbyFor(const Member& member) const;\n"
        "    void SendLobby(qint64 now_ms);\n","world per-player view")
    header=once(header,
        "    BloodborneCoop::TeamLobby lobby;\n",
        "    std::function<QSet<QByteArray>(const QByteArray&)> visible_friends;\n"
        "    BloodborneCoop::TeamLobby lobby;\n","world friend resolver state")
    world=once(world,"void Service::SendLobby(qint64 now_ms) {\n",
        """// SHYT-V49-ONLINE-MUTUAL-FRIENDS: customize the visible lobby per
// authenticated recipient, using the existing account DB and TeamLobby.
bbcoop::LobbyState Service::LobbyFor(const Member& member) const {
    bbcoop::LobbyState state = lobby.StateFor(member.lobby);
    if (!visible_friends || member.online_id.isEmpty())
        return state;
    const QSet<QByteArray> friends = visible_friends(member.online_id);
    QSet<QByteArray> friendMembers;
    for (const QByteArray& id : friends) {
        if (!id.isEmpty() && id.size() <= 32)
            friendMembers.insert(id.toHex());
    }
    for (auto& player : *state.mutable_players()) {
        if (friendMembers.contains(QByteArray::fromStdString(player.member())))
            player.set_mutual_friend(true);
    }
    return state;
}

void Service::SendLobby(qint64 now_ms) {
""",
        "per-recipient friend state")
    if world.count("lobby.StateFor(member.lobby)") < 2:
        raise ValueError("V49 expected genuine recipient lobby sends")
    # Preserve the one lookup inside LobbyFor; replace only other actual sends.
    world=world.replace("*envelope.mutable_lobby_state() = lobby.StateFor(member.lobby);",
                        "*envelope.mutable_lobby_state() = LobbyFor(member);")
    if world.count("*envelope.mutable_lobby_state() = LobbyFor(member);") < 2:
        raise ValueError("V49 actual lobby sends not annotated")
    link=once(link,"#include <QRandomGenerator>\n",
        "#include <QRandomGenerator>\n#include <QSet>\n","link Qt includes")
    link=once(link,"    m_world.RequireAuthenticatedIdentity();\n",
        """    m_world.RequireAuthenticatedIdentity();
    // SHYT-V49-ONLINE-MUTUAL-FRIENDS: social data comes from the same
    // authenticated SQLite accounts used by friendList WebAPI. Do not trust
    // character display names, client-supplied flags or arbitrary session IDs.
    m_world.SetVisibleFriends([this](const QByteArray& account) {
        QSet<QByteArray> result;
        const auto userId = m_db.GetUserId(QString::fromUtf8(account));
        if (!userId)
            return result;
        const auto relations = m_db.GetRelationships(*userId);
        const auto blockedMask = static_cast<uint8_t>(FriendStatus::Blocked);
        for (const auto& fr : relations.friends) {
            const auto [status, pair] = m_db.GetRelStatus(*userId, fr.first);
            if (status != Database::RelResult::Ok ||
                ((pair.caller | pair.other) & blockedMask) != 0)
                continue;
            {
                QReadLocker lock(&m_shared->clientsLock);
                const auto live = m_shared->clients.constFind(fr.first);
                if (live != m_shared->clients.constEnd() && live->appearOffline)
                    continue;
            }
            result.insert(fr.second.toUtf8());
        }
        return result;
    });
""","link authenticated friends")
    api=once(api,"    int ready; /* a member's */\n",
        "    int ready; /* a member's */\n"
        "    int mutual_friend; /* server-confirmed relationship, 0 for other users */\n",
        "client mutual friend flag")
    impl=once(impl,"        out.state = LobbyStateOf(player.state());\n",
        "        out.state = LobbyStateOf(player.state());\n"
        "        out.mutual_friend = player.mutual_friend() ? 1 : 0;\n",
        "client lobby friend decoding")
    # Important: priority-sort mutual friends into the bounded 16-player list.
    impl=once(impl,
        "    for (const bbcoop::LobbyPlayer& player : state->players()) {\n"
        "        const bool mine = state->has_team() && player.team() == state->team().id();\n",
        "    for (int friends_first = 1; friends_first >= 0; --friends_first) {\n"
        "      for (const bbcoop::LobbyPlayer& player : state->players()) {\n"
        "        if (static_cast<int>(player.mutual_friend()) != friends_first) continue;\n"
        "        const bool mine = state->has_team() && player.team() == state->team().id();\n",
        "client prioritizes friend list")
    impl=once(impl,
        "        out.mutual_friend = player.mutual_friend() ? 1 : 0;\n"
        "    }\n"
        "    for (const bbcoop::TeamInvite& invite : state->invites()) {\n",
        "        out.mutual_friend = player.mutual_friend() ? 1 : 0;\n"
        "      }\n"
        "    }\n"
        "    for (const bbcoop::TeamInvite& invite : state->invites()) {\n",
        "client friend priority nesting")
    ui=once(ui,
        "    // The players online (invite) and the invitations.\n",
        "    // SHYT-V49-ONLINE-MUTUAL-FRIENDS: local in-game filter for online\n"
        "    // mutual friends. The server owns the relationship flag; no GUI-only\n"
        "    // security checks and no unimplemented Join/Invade buttons.\n"
        "    static bool show_mutual_friends_only = false;\n"
        "    // The players online (invite) and the invitations.\n",
        "team UI friend filter state")
    ui=once(ui,
        '    draw->AddText(ImVec2(left_x, lists_y), Gold(), T("Hunters online", "Охотники в сети"));\n',
        '    draw->AddText(ImVec2(left_x, lists_y), Gold(),\n'
        '                  show_mutual_friends_only ? T("Friends online", "Друзья в сети")\n'
        '                                           : T("Hunters online", "Охотники в сети"));\n',
        "team friend filter heading")
    ui=once(ui,
        "    const bool can_invite = lobby.in_team && lobby.member_count < BBCOOP_LOBBY_TEAM;\n",
        "    const bool can_invite = lobby.in_team && lobby.member_count < BBCOOP_LOBBY_TEAM;\n"
        '    if (Button(draw, "shyt-mutual-friends-filter",\n'
        '               show_mutual_friends_only ? T("Show all", "Все игроки")\n'
        '                                        : T("Friends", "Друзья"),\n'
        '               ImVec2(left_x + list_w - S(155.0f), lists_y),\n'
        '               ImVec2(S(150.0f), S(31.0f)))) {\n'
        '        show_mutual_friends_only = !show_mutual_friends_only;\n'
        '    }\n',
        "team friend toggle button")
    ui=once(ui,
        '    if (lobby.player_count == 0) {\n'
        '        draw->AddText(ImVec2(left_x, y + S(8.0f)), Dim(), T("Nobody else is online", "Больше никого нет в сети"));\n'
        '    }\n'
        '    for (int i = 0; i < lobby.player_count && i < rows; ++i, y += row_h) {\n'
        '        const bbcoop_lobby_entry& p = lobby.players[i];\n',
        '    int eligible_players = 0;\n'
        '    for (int i = 0; i < lobby.player_count; ++i)\n'
        '        if (!show_mutual_friends_only || lobby.players[i].mutual_friend) ++eligible_players;\n'
        '    if (eligible_players == 0) {\n'
        '        draw->AddText(ImVec2(left_x, y + S(8.0f)), Dim(),\n'
        '                      show_mutual_friends_only ? T("No friends online", "Друзей нет в сети")\n'
        '                                               : T("Nobody else is online", "Больше никого нет в сети"));\n'
        '    }\n'
        '    int displayed_players = 0;\n'
        '    for (int i = 0; i < lobby.player_count && displayed_players < rows; ++i) {\n'
        '        const bbcoop_lobby_entry& p = lobby.players[i];\n'
        '        if (show_mutual_friends_only && !p.mutual_friend) continue;\n'
        '        ++displayed_players;\n',
        "team filtered rows")
    ui=once(ui,
        '        draw->AddText(ImVec2(left_x + S(8.0f), y + S(8.0f)), Plain(),\n'
        '                      Fit(p.name, state_x - left_x - S(24.0f)).c_str());\n',
        '        const std::string display_name =\n'
        '            p.mutual_friend ? std::string("[F] ") + p.name : std::string(p.name);\n'
        '        draw->AddText(ImVec2(left_x + S(8.0f), y + S(8.0f)), Plain(),\n'
        '                      Fit(display_name.c_str(), state_x - left_x - S(24.0f)).c_str());\n',
        "team mutual label")
    ui=once(ui,
        "            bbcoop_lobby_request(BBCOOP_TEAM_INVITE, p.id);\n"
        "        }\n"
        "    }\n"
        "    y = lists_y + S(50.0f);\n",
        "            bbcoop_lobby_request(BBCOOP_TEAM_INVITE, p.id);\n"
        "        }\n"
        "        y += row_h;\n"
        "    }\n"
        "    y = lists_y + S(50.0f);\n",
        "team row advance")
    return {PROTO:proto,WORLD:world,WORLD_H:header,LINK:link,API:api,IMPL:impl,UI:ui}
