#!/usr/bin/env python3
"""V184: source-locked original C++ regression of non-hosted lobby limits."""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE="server/tests/test_team_lobby.cpp"
MARK="SHYT_V184_NONHOSTED_LOBBY_CTEST"
INSERT_AT="int main() {"
CPP_TEST="""// SHYT_V184_NONHOSTED_LOBBY_CTEST: actual compiled original Qt TeamLobby.
static int LobbyOnlyLimitsKeepInvitesAndNonHostedWorlds() {
  TeamLobby lobby = NewLobby();
  for (int n=0; n<40; ++n) {
    const auto id=std::string("p")+std::to_string(n);
    lobby.Arrive(id,id,false);
  }
  CHECK(lobby.StateFor("p0").players_size()==39);
  lobby.SetLobbyCap(3);
  CHECK(!lobby.Hosted());
  CHECK(lobby.StateFor("p0").players_size()==3);
  CHECK(lobby.Request("p0",Request(Action::CREATE)).changed);
  CHECK(lobby.Request("p0",Request(Action::INVITE,"p35")).changed);
  const auto inviter=lobby.StateFor("p0");
  CHECK(std::ranges::any_of(inviter.players(),[](const auto& p) {
    return p.member()=="p35";
  }));
  const auto invited=lobby.StateFor("p35");
  CHECK(std::ranges::any_of(invited.players(),[](const auto& p) {
    return p.member()=="p0";
  }));
  TeamLobby worlds=NewLobby();
  worlds.Arrive("a","a",false);
  worlds.Arrive("b","b",false);
  const std::string world=PlayAWorld(worlds,"a","b");
  CHECK(!world.empty());
  worlds.Arrive("c","c",false);
  worlds.SetLobbyCap(1);
  CHECK(!worlds.Hosted());
  CHECK(worlds.StateFor("c").worlds_size()==1);
  return 0;
}

"""
MAIN_OLD="  failed |= AHostedLobbyListsFewOthers();"
MAIN_NEW=MAIN_OLD+"\n  failed |= LobbyOnlyLimitsKeepInvitesAndNonHostedWorlds();"

def patch(src: str) -> str:
    if MARK in src or src.count(INSERT_AT)!=1 or src.count(MAIN_OLD)!=1:
        raise ValueError("V184 pinned Qt native test source drift")
    return src.replace(INSERT_AT,CPP_TEST+INSERT_AT,1).replace(MAIN_OLD,MAIN_NEW,1)

def stage(root: Path) -> None:
    root=root.resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                               text=True,stderr=subprocess.DEVNULL).strip()!=PIN:
        raise ValueError("V184 pinned original only")
    path=root/FILE
    if not path.is_file() or path.is_symlink():
        raise ValueError("V184 original test source missing")
    path.write_text(patch(path.read_text(encoding="utf-8")),encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_V184_ORIGINAL_QT_LOBBY_CAP_CPP_TEST_STAGED")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: stage_cls_lobby_cpp_test_v184.py PINNED_YT130")
    stage(Path(sys.argv[1]))
