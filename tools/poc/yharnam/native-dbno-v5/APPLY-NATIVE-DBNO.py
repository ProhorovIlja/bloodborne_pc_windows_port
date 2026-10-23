#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pinned Yharnam Together source patch: native game DBNO option -> shadNet -> death hook.
Developer tool. Does not touch production, original checkout, installed games, or saves.
"""
import argparse
from pathlib import Path
import subprocess
PIN="77e350743a7cb4524cfcc1782fb6e3af64e25b15"

def changes():
    return {
"server/coop/coop.proto":[
("        FORGET_WORLD = 11;\n","        FORGET_WORLD = 11;\n        SET_DBNO = 12; // host sets Down But Not Out before Start\n"),
("    string world = 6;\n}\n\nmessage LobbyPlayer {","    string world = 6;\n    bool dbno_enabled = 7;\n}\n\nmessage LobbyPlayer {"),
("    string party = 7;\n}\n\nmessage TeamInvite {","    string party = 7;\n    optional bool dbno_enabled = 8; // absent for old teams = ON\n}\n\nmessage TeamInvite {")],
"server/coop/team_lobby.cpp":[
("        team.set_leader(member);\n        bbcoop::TeamMember& m = *team.add_members();",
 "        team.set_leader(member);\n        team.set_dbno_enabled(true);\n        bbcoop::TeamMember& m = *team.add_members();"),
("    switch (request.action()) {\n    case Action::CREATE: {",
 """    switch (request.action()) {
    case Action::SET_DBNO: {
        if (!mine || mine->leader() != member) {
            return refuse("only the team's leader changes DBNO");
        }
        if (mine->started()) {
            return refuse("DBNO is locked after the hunt starts");
        }
        if (mine->has_dbno_enabled() && mine->dbno_enabled() == request.dbno_enabled()) {
            return {};
        }
        mine->set_dbno_enabled(request.dbno_enabled());
        return {.changed = true};
    }
    case Action::CREATE: {""")],
"emulator/src/core/bloodborne_re_internal.h":[
("void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id);",
 "void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id);\nvoid TeamSetDbno(bool enabled);\nbool TeamDbnoEnabled();")],
"emulator/src/core/bloodborne_server_world.cpp":[
("std::string TeamLobbyMember() {\n",
 """bool TeamDbnoEnabled() {
    std::scoped_lock lock{team_mutex};
    const auto& state = team_gate.Lobby();
    if (!team_switch || !state || !state->has_team()) {
        return true; // preserve current native DBNO on old/non-team sessions
    }
    const bbcoop::Team& team = state->team();
    return !team.has_dbno_enabled() || team.dbno_enabled();
}

std::string TeamLobbyMember() {
"""),
("void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id) {",
 """void TeamSetDbno(bool enabled) {
    bbcoop::Envelope envelope;
    auto& request = *envelope.mutable_team_request();
    request.set_action(bbcoop::TeamRequest::SET_DBNO);
    request.set_dbno_enabled(enabled);
    QueueLobby(std::move(envelope));
}

void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id) {""")],
"emulator/src/core/bloodborne_party_death.cpp":[
("void TickPartyDeath() {\n    if (!party_death_hook_installed) {",
 """void TickPartyDeath() {
    // The host's setting is broadcast in LobbyState by shadNet.
    // Server locks it once the hunt has started.
    if (!TeamDbnoEnabled()) {
        party_death_data.store(0, std::memory_order_relaxed);
        party_death_armed.store(false, std::memory_order_relaxed);
        party_death_down.store(false, std::memory_order_relaxed);
        PostVitalsWithoutPartyDeath();
        SetPartyPanel({});
        return;
    }
    if (!party_death_hook_installed) {""")],
"bbport/gpu/bbcoop.h":[
("    bbcoop_lobby_world worlds[BBCOOP_LOBBY_WORLDS];\n} bbcoop_lobby;",
 "    bbcoop_lobby_world worlds[BBCOOP_LOBBY_WORLDS];\n    int dbno_enabled;\n} bbcoop_lobby;"),
("void bbcoop_lobby_request(int action, const char *id);",
 "void bbcoop_lobby_request(int action, const char *id);\nvoid bbcoop_team_set_dbno(int enabled);")],
"bbport/gpu/bbcoop/coop.cpp":[
("        lobby->started = team.started();",
 "        lobby->started = team.started();\n        lobby->dbno_enabled = !team.has_dbno_enabled() || team.dbno_enabled();"),
('extern "C" void bbcoop_lobby_request(int action, const char* id) {',
 '''extern "C" void bbcoop_team_set_dbno(int enabled) {
    Core::Bloodborne::Coop::TeamSetDbno(enabled != 0);
}

extern "C" void bbcoop_lobby_request(int action, const char* id) {''')],
"bbport/gpu/shim/bbport_overlay.cpp":[
("    // Title and the team's state.\n    ImGui::PushFont(MenuArt::Font(), 40.0f);",
 """    // Seamless Hunt: the same Team menu from the game's System menu and title.
    // The existing Button supports keyboard, controller and mouse focus.
    if (lobby.in_team) {
        ImGui::PushFont(MenuArt::Font(), 18.0f);
        const std::string dbno_text = lobby.dbno_enabled
            ? T("DBNO: On", "Возрождение: вкл")
            : T("DBNO: Off", "Возрождение: выкл");
        if (Button(draw, "sh-dbno", dbno_text.c_str(),
                   ImVec2(x1 - S(240.0f), win.y + S(24.0f)),
                   ImVec2(S(225.0f), S(40.0f)),
                   lobby.leader && !lobby.started)) {
            bbcoop_team_set_dbno(!lobby.dbno_enabled);
        }
        ImGui::PopFont();
    }

    // Title and the team's state.
    ImGui::PushFont(MenuArt::Font(), 40.0f);""")],
    }

def apply(checkout,out):
    checkout=checkout.resolve();out=out.resolve()
    if checkout==out or checkout in out.parents:
        raise ValueError("Output must be outside original source tree")
    actual=subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()
    if actual!=PIN:raise ValueError(f"Wrong upstream commit: {actual}, requires {PIN}")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Destination must be empty")
    result={}
    for path,patches in changes().items():
        original=(checkout/path).read_text("utf-8")
        modified=original
        for old,new in patches:
            if modified.count(old)!=1:
                raise ValueError(f"Anchor mismatch in {path}: expected once, found {modified.count(old)}")
            if new in modified:
                raise ValueError(f"Already patched: {path}")
            modified=modified.replace(old,new,1)
        result[path]=modified
    for path,source in result.items():
        dest=out/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(source,"utf-8")
    print("PATCH_OK:",len(result),"upstream files; isolated output:",out)
    print("This is NOT a compiled gameplay client or tested online session.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--checkout",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    apply(args.checkout,args.out)
