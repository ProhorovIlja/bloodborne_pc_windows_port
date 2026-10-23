#!/usr/bin/env python3
"""Pinned V11 team-screen resume patch, applied AFTER V5 DBNO and V3 UI.
Fail closed; caller stages source and handles copying/atomicity.
"""
def one(text,needle,replacement,label):
    count=text.count(needle)
    if count!=1:raise ValueError(f"{label}: expected one anchor; found {count}")
    return text.replace(needle,replacement,1)

def transform(source,header):
    out=dict(source)
    path="emulator/src/core/bloodborne_server_world.cpp"
    s=out[path]
    s=one(s,'#include "core/bloodborne_team.h"',
      '#include "core/bloodborne_team.h"\n#include "core/last_session_policy.hpp"',"header")
    s=one(s,"TeamGate team_gate;",'''TeamGate team_gate;
// Only title-screen load recovery is optional. In-game link recovery is not.
std::atomic<bool> sh_resume_title_pending{false};
bool sh_manual_title_join=false; // accessed under team_mutex
std::atomic<SeamlessHunt::Resume::Mode>& ShResumeMode(){
    static std::atomic<SeamlessHunt::Resume::Mode> mode{
        SeamlessHunt::Resume::LoadMode(
            Common::FS::GetUserPath(Common::FS::PathType::UserDir) /
            "sh_last_session_mode.txt")};
    return mode;
}
std::filesystem::path ShAnchorFile(unsigned slot){
    return Common::FS::GetUserPath(Common::FS::PathType::UserDir) /
           ("sh_last_session_" + std::to_string(slot) + ".txt");
}
''',"title state")
    s=one(s,'''        if (decision.step == TeamGate::Step::Hold) {
            return true;
        }''','''        // Never auto-load a stale or unrelated session. Require the SAME
        // active server team, party, world, member, slot and Coop protocol.
        if (decision.start && !sh_manual_title_join) {
            SeamlessHunt::Resume::Status current;
            current.member=me;
            current.team=decision.start->team();
            current.party=decision.start->party();
            current.world=decision.start->world();
            current.version=std::to_string(CoopProtocol);
            current.slot=slot;
            const auto& state=team_gate.Lobby();
            current.online=state.has_value();
            if(state && state->has_team()){
                const auto& team=state->team();
                current.member_of_team=std::ranges::any_of(team.members(),
                    [&](const auto& m){return m.member()==me;});
                current.started=team.started();
                current.compatible=team.id()==current.team &&
                    team.party()==current.party && team.world()==current.world;
            }
            const auto saved=fresh?std::optional<SeamlessHunt::Resume::Anchor>{}
                : SeamlessHunt::Resume::Load(ShAnchorFile(slot));
            auto decision_resume=SeamlessHunt::Resume::Decide(
                ShResumeMode().load(),saved,current,SeamlessHunt::Resume::NowUnix());
            if(!decision_resume.auto_join){
                sh_resume_title_pending=decision_resume.can_confirm;
                return true; // user can still press Begin manually
            }
        }
        if(decision.start){
            sh_resume_title_pending=false;
            sh_manual_title_join=false;
            SeamlessHunt::Resume::Save(ShAnchorFile(slot),
                {me,decision.start->team(),decision.start->party(),
                 decision.start->world(),std::to_string(CoopProtocol),
                 slot,SeamlessHunt::Resume::NowUnix()});
        }
        if (decision.step == TeamGate::Step::Hold) {
            return true;
        }''',"gate")
    s=one(s,'''void TeamChoose(TeamGate::Choice choice) {
    std::scoped_lock lock{team_mutex};''','''void TeamChoose(TeamGate::Choice choice) {
    std::scoped_lock lock{team_mutex};
    if(choice==TeamGate::Choice::Start)sh_manual_title_join=true;''',"manual title")
    s=one(s,'''void TeamBackAtTitle() {
    if (!team_switch) {''','''void TeamBackAtTitle() {
    sh_resume_title_pending=false;
    if (!team_switch) {''',"title state reset")
    s=one(s,'''    if (lobby_playing || team_gate.Holding()) {
        team_gate.Reset();''','''    if (lobby_playing || team_gate.Holding()) {
        sh_manual_title_join=false;
        team_gate.Reset();''',"manual reset")
    s=one(s,"std::optional<bbcoop::LobbyState> TeamLobbyState() {",'''int TeamReconnectMode(){return static_cast<int>(ShResumeMode().load());}
void TeamReconnectSetMode(int value){
    if(value<0 || value>2)return;
    auto mode=static_cast<SeamlessHunt::Resume::Mode>(value);
    ShResumeMode().store(mode);
    SeamlessHunt::Resume::SaveMode(
        Common::FS::GetUserPath(Common::FS::PathType::UserDir) /
        "sh_last_session_mode.txt",mode);
}
bool TeamReconnectPending(){return sh_resume_title_pending.load();}
void TeamReconnectConfirm(){
    std::scoped_lock lock{team_mutex};
    if(team_gate.Holding() && team_gate.Start() && !lobby_playing)
        sh_manual_title_join=true;
}
std::optional<bbcoop::LobbyState> TeamLobbyState() {''',"native callbacks")
    out[path]=s
    path="emulator/src/core/bloodborne_re_internal.h"
    out[path]=one(out[path],"void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id);",'''void TeamLobbyRequest(bbcoop::TeamRequest::Action action, const std::string& id);
int TeamReconnectMode();
void TeamReconnectSetMode(int);
bool TeamReconnectPending();
void TeamReconnectConfirm();''',"declarations")
    path="bbport/gpu/bbcoop.h"
    out[path]=one(out[path],"void bbcoop_lobby_request(int action, const char *id);",'''void bbcoop_lobby_request(int action, const char *id);
int bbcoop_reconnect_mode(void);
void bbcoop_reconnect_set_mode(int);
int bbcoop_reconnect_pending(void);
void bbcoop_reconnect_confirm(void);''',"C API")
    path="bbport/gpu/bbcoop/coop.cpp"
    out[path]=one(out[path],'extern "C" int bbcoop_lobby_view(bbcoop_lobby* lobby) {','''extern "C" int bbcoop_reconnect_mode(void){return Core::Bloodborne::Coop::TeamReconnectMode();}
extern "C" void bbcoop_reconnect_set_mode(int value){
    Core::Bloodborne::Coop::TeamReconnectSetMode(value);
}
extern "C" int bbcoop_reconnect_pending(void){
    return Core::Bloodborne::Coop::TeamReconnectPending()?1:0;
}
extern "C" void bbcoop_reconnect_confirm(void){
    Core::Bloodborne::Coop::TeamReconnectConfirm();
}
extern "C" int bbcoop_lobby_view(bbcoop_lobby* lobby) {''',"bridge")
    path="bbport/gpu/shim/bbport_overlay.cpp"
    s=out[path]
    s=one(s,'''    // Title and the team's state.
    ImGui::PushFont(MenuArt::Font(), 40.0f);''','''    // Rejoin preference lives in the game's existing Team UI, NOT launcher.
    ImGui::PushFont(MenuArt::Font(), 18.0f);
    const int resume_mode=bbcoop_reconnect_mode();
    const char* resume_label=resume_mode==2?T("Auto","Авто"):
        resume_mode==1?T("Ask","Спросить"):T("Off","Выкл");
    const std::string resume_text=std::string(T("Rejoin: ","Возврат: "))+resume_label;
    if(Button(draw,"sh-resume-mode",resume_text.c_str(),
              ImVec2(win.x+S(36.0f),win.y+S(66.0f)),
              ImVec2(S(270.0f),S(38.0f)))){
        bbcoop_reconnect_set_mode((resume_mode+1)%3);
    }
    ImGui::PopFont();
    // Title and the team's state.
    ImGui::PushFont(MenuArt::Font(), 40.0f);''',"menu option")
    s=one(s,'''        bbcoop_team_choose(lobby.in_team ? BBCOOP_TEAM_GO_START : BBCOOP_TEAM_GO_ALONE);''','''        if(lobby.in_team && lobby.started && bbcoop_reconnect_pending())
            bbcoop_reconnect_confirm();
        bbcoop_team_choose(lobby.in_team ? BBCOOP_TEAM_GO_START : BBCOOP_TEAM_GO_ALONE);''',"manual resume")
    out[path]=s
    out["emulator/src/core/last_session_policy.hpp"]=header
    return out
