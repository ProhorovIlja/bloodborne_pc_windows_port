// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <string_view>
#include <chrono>
namespace SeamlessHunt::Resume {
enum class Mode { Off, Ask, Auto };
struct Anchor {std::string member,team,party,world,version; unsigned slot=0; std::int64_t saved_at=0;};
struct Status {std::string member,team,party,world,version; unsigned slot=0; bool online=false,member_of_team=false,started=false,compatible=false;};
struct Decision {bool auto_join=false,can_confirm=false;};
inline bool Safe(std::string_view s){
 if(s.empty()||s.size()>128)return false;
 for(unsigned char c:s)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c==':'||c=='.'))return false;
 return true;
}
inline bool Valid(const Anchor& a){return Safe(a.member)&&Safe(a.team)&&Safe(a.party)&&Safe(a.world)&&Safe(a.version)&&a.slot<1000&&a.saved_at>0;}
inline Decision Decide(Mode mode,const std::optional<Anchor>& saved,const Status& s,std::int64_t now){
 if(!s.online||!s.member_of_team||!s.started||!s.compatible||!Safe(s.member)||!Safe(s.team)||!Safe(s.party)||!Safe(s.world)||!Safe(s.version))return {};
 if(!saved||!Valid(*saved))return {false,true};
 if(saved->member!=s.member)return {};
 if(saved->slot!=s.slot||saved->version!=s.version||saved->team!=s.team||saved->party!=s.party||saved->world!=s.world)return {false,true};
 if(now<saved->saved_at||now-saved->saved_at>86400)return {false,true};
 return {mode==Mode::Auto,true};
}
inline std::int64_t NowUnix(){return std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count();}
inline Mode LoadMode(const std::filesystem::path& p){std::ifstream f(p);std::string s;if(!std::getline(f,s))return Mode::Ask;return s=="auto"?Mode::Auto:s=="off"?Mode::Off:Mode::Ask;}
inline bool SaveMode(const std::filesystem::path& p,Mode m){std::ofstream f(p,std::ios::trunc);if(!f)return false;f<<(m==Mode::Auto?"auto":m==Mode::Off?"off":"ask")<<'\n';return bool(f);}
inline std::optional<Anchor> Load(const std::filesystem::path& p){
 std::ifstream f(p);std::string v;if(!std::getline(f,v)||v!="SH-RESUME-V1")return {};
 Anchor a;std::string slot,stamp,extra;
 if(!std::getline(f,a.member)||!std::getline(f,a.team)||!std::getline(f,a.party)||!std::getline(f,a.world)||!std::getline(f,a.version)||!std::getline(f,slot)||!std::getline(f,stamp)||std::getline(f,extra))return {};
 try{std::size_t n=0;auto t=std::stoul(slot,&n);if(n!=slot.size()||t>=1000)return {};a.slot=t;n=0;a.saved_at=std::stoll(stamp,&n);if(n!=stamp.size())return {};}catch(...){return {};}
 return Valid(a)?std::optional<Anchor>{a}:std::nullopt;
}
inline bool Save(const std::filesystem::path& p,const Anchor& a){
 if(!Valid(a))return false;std::ofstream f(p,std::ios::trunc);if(!f)return false;
 f<<"SH-RESUME-V1\n"<<a.member<<'\n'<<a.team<<'\n'<<a.party<<'\n'<<a.world<<'\n'<<a.version<<'\n'<<a.slot<<'\n'<<a.saved_at<<'\n';return bool(f);
}
}
