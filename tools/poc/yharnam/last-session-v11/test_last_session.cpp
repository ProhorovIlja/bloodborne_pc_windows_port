#ifdef NDEBUG
#undef NDEBUG
#endif
#include "last_session_policy.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::Resume;
int main(){
 const Anchor anchor{"alice","team123","world:w1","w1","8",2,100000};
 const Status active{"alice","team123","world:w1","w1","8",2,true,true,true,true};
 assert(Decide(Mode::Auto,anchor,active,100100).auto_join);
 assert(!Decide(Mode::Ask,anchor,active,100100).auto_join);
 assert(Decide(Mode::Ask,anchor,active,100100).can_confirm);
 assert(!Decide(Mode::Off,anchor,active,100100).auto_join);
 assert(!Decide(Mode::Auto,{},active,100100).auto_join);
 auto changed=active;changed.team="other";assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.party="world:w2";assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.world="w2";assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.member="bob";assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.slot=3;assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.version="9";assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.started=false;assert(!Decide(Mode::Auto,anchor,changed,100100).can_confirm);
 changed=active;changed.online=false;assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 changed=active;changed.member_of_team=false;assert(!Decide(Mode::Auto,anchor,changed,100100).auto_join);
 assert(!Decide(Mode::Auto,anchor,active,100000+86401).auto_join);
 assert(!Decide(Mode::Auto,anchor,active,99999).auto_join);
 assert(!Safe("abc/def"));assert(!Safe("a\nb"));
 const auto root=std::filesystem::temp_directory_path()/"sh_v11_git_test";
 std::filesystem::create_directories(root);
 assert(SaveMode(root/"mode",Mode::Auto));
 assert(LoadMode(root/"mode")==Mode::Auto);
 assert(SaveMode(root/"mode",Mode::Off));
 assert(LoadMode(root/"mode")==Mode::Off);
 assert(Save(root/"anchor",anchor));
 auto round=Load(root/"anchor");assert(round&&round->team==anchor.team);
 {std::ofstream f(root/"anchor",std::ios::trunc);f<<"bad\n";}
 assert(!Load(root/"anchor"));
 std::filesystem::remove_all(root);
 std::cout<<"PASS: preference, identity, stale sessions and title resume safety\n";
}
