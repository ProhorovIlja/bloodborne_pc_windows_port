// V13: camera-only spectator when the local member is down/dead.
namespace Spectator {
SeamlessHunt::Spectate::State state;
std::vector<SeamlessHunt::Spectate::Hunter> hunters;
void Tick() {
    const bool covered=menu_open || quit_open || Team::open || Joining::open || Map::open;
    const auto& panel=Party::panel;
    const auto own=static_cast<SeamlessHunt::Spectate::Life>(panel.vital);
    hunters.clear();
    for(int i=0;i<panel.member_count;++i){
        const auto& m=panel.members[i];
        hunters.push_back({m.name,
            static_cast<SeamlessHunt::Spectate::Life>(m.vital),
            m.here!=0,m.has_at!=0,{m.x,m.y,m.z}});
    }
    state.Update(own,hunters);
    if(covered || state.mode==SeamlessHunt::Spectate::Mode::Inactive){
        runtime_camhook_spectator(0,0,0,0,0,0,0);
        return;
    }
    // Keyboard F/F1, plus gamepad Triangle/Square.
    if(ImGui::IsKeyPressed(ImGuiKey_F,false) ||
       ImGui::IsKeyPressed(ImGuiKey_GamepadFaceUp,false))state.Follow(hunters);
    if(ImGui::IsKeyPressed(ImGuiKey_F1,false) ||
       ImGui::IsKeyPressed(ImGuiKey_GamepadFaceLeft,false))state.Free();
    if(state.mode==SeamlessHunt::Spectate::Mode::Follow){
        if(ImGui::IsKeyPressed(ImGuiKey_A,false) ||
           ImGui::IsKeyPressed(ImGuiKey_GamepadL1,false))state.Cycle(-1,hunters);
        if(ImGui::IsKeyPressed(ImGuiKey_D,false) ||
           ImGui::IsKeyPressed(ImGuiKey_GamepadR1,false))state.Cycle(+1,hunters);
    }
    float target[3]{};
    if(state.mode==SeamlessHunt::Spectate::Mode::Follow){
        if(state.selected<0 || state.selected>=static_cast<int>(hunters.size()))return;
        const auto& t=hunters[static_cast<std::size_t>(state.selected)];
        if(!SeamlessHunt::Spectate::Valid(t))return;
        std::copy(t.position.begin(),t.position.end(),target);
    }
    float strafe=0,rise=0,forward=0;
    if(state.mode==SeamlessHunt::Spectate::Mode::Free){
        const float dt=std::clamp(ImGui::GetIO().DeltaTime,0.0f,0.04f);
        const float speed=(ImGui::IsKeyDown(ImGuiKey_LeftShift)||
                           ImGui::IsKeyDown(ImGuiKey_GamepadR2))?9.0f:4.0f;
        const float step=dt*speed;
        strafe=step*(int(ImGui::IsKeyDown(ImGuiKey_D))-int(ImGui::IsKeyDown(ImGuiKey_A)));
        rise=step*(int(ImGui::IsKeyDown(ImGuiKey_Space))-int(ImGui::IsKeyDown(ImGuiKey_LeftCtrl)));
        forward=step*(int(ImGui::IsKeyDown(ImGuiKey_W))-int(ImGui::IsKeyDown(ImGuiKey_S)));
        strafe+=step*(int(ImGui::IsKeyDown(ImGuiKey_GamepadLStickRight))-
                      int(ImGui::IsKeyDown(ImGuiKey_GamepadLStickLeft)));
        forward+=step*(int(ImGui::IsKeyDown(ImGuiKey_GamepadLStickUp))-
                       int(ImGui::IsKeyDown(ImGuiKey_GamepadLStickDown)));
        rise+=step*(int(ImGui::IsKeyDown(ImGuiKey_GamepadDpadUp))-
                    int(ImGui::IsKeyDown(ImGuiKey_GamepadDpadDown)));
    }
    runtime_camhook_spectator(static_cast<int>(state.mode),target[0],target[1],target[2],
                              strafe,rise,forward);
    const char* label=state.mode==SeamlessHunt::Spectate::Mode::Follow
        ? T("Spectating hunter", "Наблюдение за охотником")
        : T("Free camera", "Свободная камера");
    const ImVec2 size=ImGui::GetIO().DisplaySize;
    ImGui::SetNextWindowPos(ImVec2(size.x*0.5f,size.y-96.0f),ImGuiCond_Always,ImVec2(0.5f,0));
    ImGui::SetNextWindowBgAlpha(0.65f);
    ImGui::Begin("##sh-v13-spectator",nullptr,ImGuiWindowFlags_NoDecoration|
        ImGuiWindowFlags_NoInputs|ImGuiWindowFlags_AlwaysAutoResize|
        ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoFocusOnAppearing);
    ImGui::TextUnformatted(label);
    if(state.mode==SeamlessHunt::Spectate::Mode::Follow){
        const char* name=hunters[static_cast<std::size_t>(state.selected)].name.c_str();
        ImGui::TextUnformatted(name[0]?name:T("Hunter", "Охотник"));
        ImGui::TextDisabled("A / D, L1 / R1 | F1 / Square: Free Cam");
    }else ImGui::TextDisabled("WASD + mouse | F / Triangle: Follow");
    ImGui::End();
}
} // namespace Spectator
