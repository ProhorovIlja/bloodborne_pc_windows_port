// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// User-controlled in-game UI scale, isolated to the port's BB_USER_DIR.
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
namespace SeamlessHunt::InGame {
inline std::string UiScalePath() {
    const char* dir=std::getenv("BB_USER_DIR");
    if(!dir||!*dir)return {};
    return std::string(dir)+"/seamless-hunt-ui-scale.txt";
}
inline int& TeamScalePercent() {
    static int percent=[] {
        int loaded=100;
        const std::string path=UiScalePath();
        if(!path.empty()) {
            if(FILE* f=std::fopen(path.c_str(),"rb")) {
                const bool valid=std::fscanf(f,"%d",&loaded)==1;
                std::fclose(f);
                if(!valid||loaded<70||loaded>110||loaded%5!=0)loaded=100;
            }
        }
        return loaded;
    }();
    return percent;
}
inline float GetTeamScale(){return TeamScalePercent()/100.0f;}
inline int SetTeamScalePercent(int requested){
    const int v=std::clamp((requested+2)/5*5,70,110);
    int& current=TeamScalePercent();
    if(v==current)return current;
    current=v;
    const std::string path=UiScalePath();
    if(!path.empty())if(FILE* f=std::fopen(path.c_str(),"wb")){
        std::fprintf(f,"%d\n",current);std::fclose(f);
    }
    return current;
}
} // namespace SeamlessHunt::InGame
