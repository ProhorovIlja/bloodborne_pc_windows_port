#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V455: extract and compile *actual original BBHost mode_of/wanted_fps* seams.

The runner first stages original CLS v1.4.0 into exact BBHost v0.2.26.
Only then this harness extracts the two complete functions, recompiles them,
and exercises offline and online settings against original engine policy.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

MARKER='int wanted_fps() {'
MODE_MARKER='int mode_of(int fps) {'
FRAMES='constexpr int kFrameRates[] = {60, 90, 120, 150, 180, 240, 360, 480, 960};'

def take_function(source:str, marker:str)->str:
    if source.count(marker)!=1:
        raise ValueError("ambiguous original BBHost function")
    start=source.index(marker)
    finish=source.find("\n}\n",start)
    if finish<0 or finish-start>1800:
        raise ValueError("unsafe or changing engine function")
    return source[start:finish+3]

def harness(text:str)->str:
    if text.count(FRAMES)!=1:raise ValueError("frame rate enumerations drift")
    source=FRAMES+"\n"+take_function(text,MODE_MARKER)+"\n"+take_function(text,MARKER)
    return (
        "#include <cstdlib>\n#include <cstdio>\n#include <cassert>\n"
        "struct FPSSettings { int frame_cap=60; };\n"
        "FPSSettings &host_settings() { static FPSSettings s; return s; }\n"
        +source+
        "\nvoid check(int setting, const char* override_fps, const char* online,"
        " const char* unlock, int wanted) {\n"
        " host_settings().frame_cap=setting;\n"
        " if(override_fps) setenv(\"BBHOST_GAME_FPS\",override_fps,1);"
        " else unsetenv(\"BBHOST_GAME_FPS\");\n"
        " if(online) setenv(\"BB_ONLINE\",online,1);"
        " else unsetenv(\"BB_ONLINE\");\n"
        " if(unlock) setenv(\"BB_ONLINE_UNLOCKED_FPS\",unlock,1);"
        " else unsetenv(\"BB_ONLINE_UNLOCKED_FPS\");\n"
        " int actual=wanted_fps();\n"
        " if(actual!=wanted) { std::fprintf(stderr,"
        " \"FPS mismatch: cap=%d override=%s online=%s unlock=%s got=%d want=%d\\n\","
        " setting,override_fps?override_fps:\"<none>\",online?online:\"<none>\","
        " unlock?unlock:\"<none>\",actual,wanted); std::abort(); }\n"
        "}\n"
        "int main() {\n"
        " check(960,nullptr,nullptr,nullptr,960);\n"
        " check(60,\"960\",nullptr,nullptr,960);\n"
        " check(60,\"uncapped\",nullptr,nullptr,0);\n"
        " check(60,\"0\",nullptr,nullptr,0);\n"
        " check(30,nullptr,nullptr,nullptr,30);\n"
        " check(960,nullptr,\"1\",nullptr,60);\n"
        " check(960,\"960\",\"1\",nullptr,60);\n"
        " check(960,\"0\",\"1\",nullptr,60);\n"
        " check(960,\"uncapped\",\"1\",nullptr,60);\n"
        " check(90,\"120\",\"1\",nullptr,60);\n"
        " check(30,\"30\",\"1\",nullptr,30);\n"
        " check(960,nullptr,\"1\",\"1\",120);\n"
        " check(960,\"960\",\"1\",\"1\",120);\n"
        " check(90,\"0\",\"1\",\"1\",120);\n"
        " check(120,nullptr,\"1\",\"1\",120);\n"
        " check(90,nullptr,\"1\",\"1\",90);\n"
        " check(60,\"360\",\"0\",nullptr,360);\n"
        " check(60,\"360\",nullptr,nullptr,360);\n"
        " std::puts(\"SHYT_V455_BBHOST_REAL_ENGINE_OFFLINE_INTACT_ONLINE_CAP_PASS\");\n"
        "}\n"
    )

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--cxx",default="clang++")
    a=p.parse_args()
    text=a.source.read_text(encoding="utf-8")
    if text.count("BBHOST_GAME_FPS")<1:
        raise SystemExit("V455_REAL_ENGINE_SNIPPET_MISSING")
    c=harness(text)
    with tempfile.TemporaryDirectory(prefix="shyt-v455-") as temp:
        src=Path(temp)/"v455.cpp"
        binary=Path(temp)/"v455"
        src.write_text(c,encoding="utf-8")
        subprocess.run([a.cxx,"-std=c++20","-O2","-Wall","-Wextra","-Werror",
                        "-pedantic",str(src),"-o",str(binary)],check=True,timeout=50)
        subprocess.run([str(binary)],check=True,timeout=15)
    print("SHYT_V455_REAL_ENGINE_SOURCE_FPS_REGRESSION_PASS")

if __name__=="__main__":
    main()
