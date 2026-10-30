#!/usr/bin/env python3
"""V113: integrate source-pinned native Hosted StateFor indexing AFTER V112 nonHosted cache.

Based on reviewed original-source PR41. Both source patches apply to the
*same disposable actual native Qt 1.3 team lobby*, not to parallel builds.
"""
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP, HEADER, TEST = ("server/coop/team_lobby.cpp", "server/coop/team_lobby.h",
                     "server/tests/test_team_lobby.cpp")
BLOBS = {
    CPP: "7978d8d8062d8c18f1db79b02551c65fba2eb261",
    HEADER: "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8",
    TEST: "c045e637ada5e548b003d34033c912fde54f1d34",
}

OLD_INDEX = """void TeamLobby::Index() const {
    team_index.clear();
    for (size_t at = 0; at < teams.size(); ++at) {
        for (const bbcoop::TeamMember& m : teams[at].members()) {
            team_index.emplace(m.member(), at);
        }
    }
    indexed = true;
}"""
NEW_INDEX = """void TeamLobby::Index() const {
    team_index.clear();
    for (size_t at = 0; at < teams.size(); ++at) {
        for (const bbcoop::TeamMember& m : teams[at].members()) {
            team_index.emplace(m.member(), at);
        }
    }
    hosted_solo_index.clear();
    hosted_invite_team_index.clear();
    if (hosted) {
        // Map iteration preserves original alphabetical roster order.
        for (const auto& [member, player] : players) {
            if (!team_index.contains(member)) {
                hosted_solo_index.push_back(member);
            }
        }
        // Keep original invited-member map order, and each invite order.
        for (const auto& [invited, list] : invites) {
            for (const bbcoop::TeamInvite& invite : list) {
                hosted_invite_team_index[invite.team()].push_back(invited);
            }
        }
    }
    indexed = true;
}"""
OLD_STATE = """        if (mine) {
            for (const auto& [invited, list_of] : invites) {
                for (const bbcoop::TeamInvite& invite : list_of) {
                    if (invite.team() == mine->id()) {
                        list(invited);
                    }
                }
            }
        }
        size_t others = 0;
        for (const auto& [other, player] : players) {
            if (others >= lobby_players) {
                break;
            }
            if (!listed.contains(other) && !TeamOf(other)) {
                list(other);
                ++others;
            }
        }"""
NEW_STATE = """        if (mine) {
            if (const auto found = hosted_invite_team_index.find(mine->id());
                found != hosted_invite_team_index.end()) {
                for (const std::string& invited : found->second) {
                    list(invited);
                }
            }
        }
        size_t others = 0;
        for (const std::string& other : hosted_solo_index) {
            if (others >= lobby_players) {
                break;
            }
            if (!listed.contains(other)) {
                list(other);
                ++others;
            }
        }"""
OLD_SET_HOSTED = """    void SetHosted(size_t lobby_players, size_t worlds_per_player) {
        hosted = true;
        this->lobby_players = lobby_players;
        this->worlds_per_player = worlds_per_player;
    }"""
NEW_SET_HOSTED = """    void SetHosted(size_t lobby_players, size_t worlds_per_player) {
        hosted = true;
        this->lobby_players = lobby_players;
        this->worlds_per_player = worlds_per_player;
        Changed(); // Rebuild hosted indices even if StateFor was previously unhosted.
    }"""

OLD_HEADER = """    mutable std::map<std::string, size_t> team_index; // member -> its team's place in `teams`"""
NEW_HEADER = OLD_HEADER + """
    // V113: Hosted indexes share the V112 Changed()/Index() lifecycle.
    mutable std::vector<std::string> hosted_solo_index;
    mutable std::map<std::string, std::vector<std::string>> hosted_invite_team_index;"""
CPP_TEST = """// 512 mostly-teamed Hosted clients must not expose a global player roster.
int HostedLargeTeamsKeepRosterBoundedThroughChanges() {
  // Original Index may have been built while not Hosted: switching modes
  // must invalidate the cache to keep its exact original player listing.
  TeamLobby after_switch = NewLobby();
  after_switch.Arrive("a", "A", false);
  after_switch.Arrive("b", "B", false);
  CHECK(after_switch.StateFor("a").players_size() == 1);
  after_switch.SetHosted(3, 16);
  CHECK(after_switch.StateFor("a").players_size() == 1);
  CHECK(after_switch.StateFor("a").players(0).member() == "b");
  TeamLobby lobby = NewLobby();
  lobby.SetHosted(3, 16);
  for (int i = 0; i < 512; ++i) {
    std::string member = "p" + std::to_string(i);
    lobby.Arrive(member, member, false);
  }
  for (int i = 0; i < 512; ++i) {
    std::string member = "p" + std::to_string(i);
    CHECK(lobby.Request(member, Request(Action::CREATE)).changed);
  }
  for (int i = 0; i < 512; ++i) {
    std::string member = "p" + std::to_string(i);
    const auto state = lobby.StateFor(member);
    CHECK(state.has_team());
    CHECK(state.players_size() == 0);
  }
  CHECK(lobby.Arrive("z0", "Zed", false).changed);
  CHECK(lobby.StateFor("p0").players_size() == 1);
  CHECK(lobby.StateFor("p0").players(0).member() == "z0");
  CHECK(lobby.StateFor("p511").players(0).name() == "Zed");
  CHECK(lobby.Request("p0", Request(Action::INVITE, "z0")).changed);
  const auto invited = lobby.StateFor("z0");
  CHECK(invited.invites_size() == 1);
  CHECK(invited.invites(0).team() == lobby.TeamOf("p0")->id());
  CHECK(lobby.Leave("z0").changed);
  CHECK(lobby.StateFor("p0").players_size() == 0);
  return 0;
}

"""
OLD_MAIN = "int main() {\n  int failed = 0;"
NEW_MAIN = "int main() {\n  int failed = 0;\n  failed |= HostedLargeTeamsKeepRosterBoundedThroughChanges();"

def unique(s, old, new, label):
    if s.count(old) != 1:
        raise ValueError("Source drift " + label)
    return s.replace(old, new)

def rewrite(cpp, header, tests):
    # A separate Hosted-only PR41 stage was clean-source-only. This version
    # requires the already-staged V112 NONHOSTED optimization in all 3 C++
    # files, refusing accidental incomplete/old Qt source combinations.
    if not all("SHYT-V112-NONHOSTED-ROSTER-CACHE" in x
               for x in (cpp, header, tests)):
        raise ValueError("V113 requires V112 original Qt source stage first")
    if "hosted_invite_team_index" in cpp or "hosted_solo_index" in header:
        raise ValueError("Double application")
    cpp = unique(cpp, OLD_INDEX, NEW_INDEX, "Index")
    cpp = unique(cpp, OLD_STATE, NEW_STATE, "Hosted StateFor")
    header = unique(header, OLD_SET_HOSTED, NEW_SET_HOSTED, "Hosted mode switch")
    header = unique(header, OLD_HEADER, NEW_HEADER, "Fields")
    tests = unique(tests, OLD_MAIN, CPP_TEST + NEW_MAIN, "Original team lobby test")
    return cpp, header, tests

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Original YT1.3 SHA changed")
    files = [root / p for p in (CPP, HEADER, TEST)]
    for path, file in zip((CPP, HEADER, TEST), files):
        if git(root, "rev-parse", "HEAD:" + path) != BLOBS[path]:
            raise ValueError("Original blob changed: " + path)
        if not file.is_file() or file.is_symlink():
            raise ValueError("Missing/linked original Qt C++ file: " + path)
        if not git(root, "diff", "--", path):
            raise ValueError("Missing required V112 previous C++ stage: " + path)
    contents = rewrite(*(p.read_text(encoding="utf-8") for p in files))
    for file, text in zip(files, contents):
        file.write_bytes(text.encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V112_V113_BOTH_LOBBY_MODES_NATIVE_QT_CPP_REGRESSION_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_pinned_official_yt130_checkout", type=Path)
    apply(parser.parse_args().disposable_pinned_official_yt130_checkout)
