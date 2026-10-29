#!/usr/bin/env python3
"""V112: source-pinned nonHosted native Qt lobby roster CPU cache.

Original TeamLobby::StateFor computes identical roster metadata for each
recipient. This stage reuses one public roster between Changed() calls.
Full original per-recipient protobuf wire, rules and auth stay unchanged.
This does NOT claim a proven 64+ player server performance improvement.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
HEADER = "server/coop/team_lobby.h"
CPP = "server/coop/team_lobby.cpp"
TEST = "server/tests/test_team_lobby.cpp"
BLOBS = {
    HEADER: "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8",
    CPP: "7978d8d8062d8c18f1db79b02551c65fba2eb261",
    TEST: "c045e637ada5e548b003d34033c912fde54f1d34",
}
TAG = "SHYT-V112-NONHOSTED-ROSTER-CACHE"
H_OLD = """    void Changed() const {
        indexed = false;
    }"""
H_NEW = """    void Changed() const {
        indexed = false;
        nonhosted_roster_valid = false; // SHYT-V112-NONHOSTED-ROSTER-CACHE
    }"""
H_MEMBERS = """    mutable std::map<std::string, size_t> team_index; // member -> its team's place in `teams`"""
H_MEMBERS_NEW = H_MEMBERS + """
    // Only nonHosted: keep the same public roster between lobby edits.
    mutable bool nonhosted_roster_valid = false;
    mutable std::vector<bbcoop::LobbyPlayer> nonhosted_roster; // SHYT-V112-NONHOSTED-ROSTER-CACHE"""
CPP_OLD = """    if (!hosted) {
        for (const auto& [other, player] : players) {
            if (other != member) {
                add_player(other, player);
            }
        }
    } else {"""
CPP_NEW = """    if (!hosted) {
        // SHYT-V112-NONHOSTED-ROSTER-CACHE: std::map order and each full
        // original state are preserved. Compute each row only once per edit.
        if (!nonhosted_roster_valid) {
            nonhosted_roster.clear();
            nonhosted_roster.reserve(players.size());
            for (const auto& [other, player] : players) {
                bbcoop::LobbyPlayer& entry = nonhosted_roster.emplace_back();
                entry.set_member(other);
                entry.set_name(player.name);
                entry.set_state(StateOf(other));
                if (const bbcoop::Team* team = TeamOf(other))
                    entry.set_team(team->id());
            }
            nonhosted_roster_valid = true;
        }
        for (const bbcoop::LobbyPlayer& entry : nonhosted_roster) {
            if (entry.member() != member)
                *state.add_players() = entry;
        }
    } else {"""
TEST_OLD = """int main() {
  int failed = 0;"""
TEST_NEW = r"""// SHYT-V112-NONHOSTED-ROSTER-CACHE: real original Qt/protobuf regression.
int NonHostedRosterCacheRefreshesAndKeepsOriginalPerRecipientSemantics() {
  TeamLobby lobby = NewLobby();
  for (int i = 0; i < 100; ++i) {
    const std::string id = "hunter" + std::to_string(i);
    lobby.Arrive(id, "Name" + std::to_string(i), false);
  }
  const auto find = [](const bbcoop::LobbyState& state,
                       const std::string& member) -> const bbcoop::LobbyPlayer* {
    for (const bbcoop::LobbyPlayer& player : state.players()) {
      if (player.member() == member)
        return &player;
    }
    return nullptr;
  };
  const auto a = lobby.StateFor("hunter0");
  const auto b = lobby.StateFor("hunter1");
  CHECK(a.players_size() == 99 && b.players_size() == 99);
  CHECK(find(a, "hunter0") == nullptr);
  CHECK(find(b, "hunter1") == nullptr);
  CHECK(find(a, "hunter1") && find(b, "hunter0"));
  CHECK(find(a, "hunter1")->name() == "Name1");
  CHECK(find(a, "hunter1")->state() == bbcoop::LobbyPlayer::TITLE);
  CHECK(lobby.StateFor("hunter0").SerializeAsString() == a.SerializeAsString());
  lobby.Arrive("hunter1", "Ada", true);
  const auto renamed = lobby.StateFor("hunter0");
  CHECK(find(renamed, "hunter1"));
  CHECK(find(renamed, "hunter1")->name() == "Ada");
  CHECK(find(renamed, "hunter1")->state() == bbcoop::LobbyPlayer::PLAYING);
  CHECK(lobby.Request("hunter0", Request(Action::CREATE)).changed);
  const std::string team = lobby.TeamOf("hunter0")->id();
  const auto teamed = lobby.StateFor("hunter1");
  CHECK(find(teamed, "hunter0") && find(teamed, "hunter0")->team() == team);
  CHECK(lobby.Request("hunter0", Request(Action::INVITE, "hunter1")).changed);
  CHECK(lobby.StateFor("hunter1").invites_size() == 1);
  CHECK(lobby.Request("hunter1", Request(Action::ACCEPT, {}, team)).changed);
  const auto joined = lobby.StateFor("hunter0");
  CHECK(find(joined, "hunter1") && find(joined, "hunter1")->team() == team);
  CHECK(lobby.StateFor("hunter1").team().members_size() == 2);
  lobby.Leave("hunter1");
  const auto gone = lobby.StateFor("hunter0");
  CHECK(gone.players_size() == 98);
  CHECK(find(gone, "hunter1") == nullptr);
  lobby.SetHosted(2, 2);
  CHECK(lobby.StateFor("hunter0").players_size() <= 2);
  return 0;
}

int main() {
  int failed = 0;
  failed |= NonHostedRosterCacheRefreshesAndKeepsOriginalPerRecipientSemantics();"""

def replace_one(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"{TAG}: original native C++ anchor drift: {label}")
    return text.replace(old, new, 1)

def rewrite(files: dict[str, str]) -> dict[str, str]:
    if set(files) != set(BLOBS):
        raise ValueError(f"{TAG}: exact original Qt source trio needed")
    h, cpp, test = (files[k] for k in (HEADER, CPP, TEST))
    if any(TAG in body for body in (h, cpp, test)):
        raise ValueError(f"{TAG}: duplicate stage denied")
    if "constexpr size_t TeamSize = 5" not in h or "GuestSigns{7, 6, 5, 4}" not in cpp:
        raise ValueError(f"{TAG}: five-hunter stage required first")
    h = replace_one(h, H_OLD, H_NEW, "Changed invalidation")
    h = replace_one(h, H_MEMBERS, H_MEMBERS_NEW, "roster member cache")
    cpp = replace_one(cpp, CPP_OLD, CPP_NEW, "nonHosted roster path")
    test = replace_one(test, TEST_OLD, TEST_NEW, "Qt team lobby regression")
    return {HEADER: h, CPP: cpp, TEST: test}

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError(f"{TAG}: wrong original YT1.3 checkout")
    paths = {rel: root / rel for rel in BLOBS}
    for rel, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{TAG}: missing or linked source {rel}")
        if git(root, "rev-parse", "HEAD:" + rel) != BLOBS[rel]:
            raise ValueError(f"{TAG}: unpinned upstream source {rel}")
        if not git(root, "diff", "--", rel):
            raise ValueError(f"{TAG}: missing prior five-hunter source stage {rel}")
    changed = rewrite({rel: path.read_text(encoding="utf-8") for rel, path in paths.items()})
    for rel, path in paths.items():
        path.write_text(changed[rel], encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print(f"{TAG}_ORIGINAL_QT_CPP_STAGED_NO_WIRE_OR_AUTH_CHANGE")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_nonhosted_roster_cache_v112.py DISPOSABLE_YT13_CLONE")
    stage(Path(sys.argv[1]))
