#!/usr/bin/env python3
"""Pin and add real YT C++ lobby-batch functional regression to disposable checkout.

Checks input/output behavior, not just source string. The test exercises
multiple valid edits before 50 ms Tick, newly arriving player's lobby, and
start/ready events, preserving both kinds of accepted team transitions.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "server/tests/test_bloodborne_world.cpp"
BLOB = "2ec55d02101545723e9889bebe83d8b1d531a1c7"

TEST = r'''
int NonHostedTeamEditsAreCoalescedAndStartStillWorks() {
  Service service{{}};
  Game leader{1000, "lead", 11};
  Game guest{1001, "guest", 12};
  const std::vector<Game *> players{&leader, &guest};
  qint64 now = 1'000'000;
  leader.LobbyHello(false, now);
  guest.LobbyHello(false, now);
  Pump(service, players, now);
  CHECK(leader.lobby_states >= 1);
  CHECK(guest.lobby_states >= 1);
  const int before_leader = leader.lobby_states;
  const int before_guest = guest.lobby_states;

  // Two legal changes arrive in one read burst before one server Tick.
  leader.Team(bbcoop::TeamRequest::CREATE, now + 100);
  leader.Team(bbcoop::TeamRequest::INVITE, now + 100, guest.name);
  Pump(service, players, now + 100);

  // Both see ONLY the final lobby snapshot, not a broadcast per edit.
  CHECK(leader.lobby_states == before_leader + 1);
  CHECK(guest.lobby_states == before_guest + 1);
  CHECK(guest.lobby.invites_size() == 1);
  const int steady = leader.lobby_states;
  Pump(service, players, now + 100);
  CHECK(leader.lobby_states == steady);

  // Joining and team-start are still genuine reliable co-op controls.
  guest.Team(bbcoop::TeamRequest::ACCEPT, now + 200, {},
             guest.lobby.invites(0).team());
  Pump(service, players, now + 200);
  leader.Team(bbcoop::TeamRequest::READY, now + 300, {}, {}, 0, "Hunter");
  guest.Team(bbcoop::TeamRequest::READY, now + 300, {}, {}, 1, "Doll");
  Pump(service, players, now + 300);
  leader.Team(bbcoop::TeamRequest::START, now + 400);
  Pump(service, players, now + 400);
  CHECK(!leader.starts.empty());
  CHECK(!guest.starts.empty());
  CHECK(leader.starts.back().party() == guest.starts.back().party());

  // A newcomer must receive its own initial LobbyState independently.
  Game newcomer{1002, "new", 13};
  newcomer.LobbyHello(false, now + 500);
  Pump(service, {&leader, &guest, &newcomer}, now + 500);
  CHECK(newcomer.lobby_states >= 1);
  return 0;
}
'''

ANCHOR = "int main() {\n  const std::vector<std::pair<const char *, std::function<int()>>> tests{\n"
NEW = ANCHOR + '      {"NonHostedTeamEditsAreCoalescedAndStartStillWorks",\n       NonHostedTeamEditsAreCoalescedAndStartStillWorks},\n'


def patch_text(text: str) -> str:
    if text.count(ANCHOR) != 1 or text.count("NonHostedTeamEditsAreCoalescedAndStartStillWorks") != 0:
        raise ValueError("Upstream C++ test source mismatch/already injected")
    return text.replace(ANCHOR, TEST + "\n" + NEW)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN or git(root, "rev-parse", "HEAD:" + FILE) != BLOB:
        raise ValueError("Unknown native server test source revision")
    path = root / FILE
    changed = patch_text(path.read_text(encoding="utf-8"))
    path.write_text(changed, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_NONHOSTED_LOBBY_FUNCTIONAL_CPP_TEST_STAGED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_official_yt_checkout", type=Path)
    apply(p.parse_args().disposable_official_yt_checkout)
