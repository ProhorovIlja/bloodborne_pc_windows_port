#!/usr/bin/env python3
"""Optimize original YT 1.3 Hosted world fan-out after exact pinned roster stage.

No wire changes. Rebuild per-member newest-first world indices on existing Changed().
All original world authorization stays per-member and non-Hosted preserves full roster.
"""
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP = "server/coop/team_lobby.cpp"
HEADER = "server/coop/team_lobby.h"
TEST = "server/tests/test_team_lobby.cpp"
BLOBS = {
    CPP: "7978d8d8062d8c18f1db79b02551c65fba2eb261",
    HEADER: "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8",
    TEST: "c045e637ada5e548b003d34033c912fde54f1d34",
}

OLD_INDEX = """        for (const auto& [invited, list] : invites) {
            for (const bbcoop::TeamInvite& invite : list) {
                hosted_invite_team_index[invite.team()].push_back(invited);
            }
        }
    }
    indexed = true;"""
NEW_INDEX = """        for (const auto& [invited, list] : invites) {
            for (const bbcoop::TeamInvite& invite : list) {
                hosted_invite_team_index[invite.team()].push_back(invited);
            }
        }
        // Worlds are already newest-first. A StateFor now visits only worlds
        // containing that signed-in member, not every other player's worlds.
        // Deduplicate unexpected member repeats to preserve original visibility.
        for (size_t at = 0; at < worlds.size(); ++at) {
            std::set<std::string> members_seen;
            for (const std::string& owner : worlds[at].members()) {
                if (members_seen.insert(owner).second) {
                    hosted_world_index[owner].push_back(at);
                }
            }
        }
    }
    indexed = true;"""
OLD_CLEAR = """    hosted_solo_index.clear();
    hosted_invite_team_index.clear();
    if (hosted) {"""
NEW_CLEAR = """    hosted_solo_index.clear();
    hosted_invite_team_index.clear();
    hosted_world_index.clear();
    if (hosted) {"""
OLD_FIELDS = """    mutable std::map<std::string, std::vector<std::string>> hosted_invite_team_index;

    std::function<std::string()> make_id;"""
NEW_FIELDS = """    mutable std::map<std::string, std::vector<std::string>> hosted_invite_team_index;
    // Source-checked Hosted member-only world view, indices into sorted worlds.
    mutable std::map<std::string, std::vector<size_t>> hosted_world_index;

    std::function<std::string()> make_id;"""
OLD_STATE = """    size_t worlds_listed = 0;
    for (const bbcoop::TeamWorldInfo& world : worlds) {
        if (hosted) {
            if (worlds_listed >= worlds_per_player || !Lists(world.members(), member)) {
                continue;
            }
            ++worlds_listed;
        }
        bbcoop::TeamWorldInfo& out = *state.add_worlds();
        out = world;
        out.clear_members();
        if (const bbcoop::Team* team = PlayedBy(world.id(), nullptr)) {
            out.set_played_by(team->id());
        }
    }"""
NEW_STATE = """    const auto publish_world = [&](const bbcoop::TeamWorldInfo& world) {
        bbcoop::TeamWorldInfo& out = *state.add_worlds();
        out = world;
        out.clear_members(); // Never reveal the server-side members list.
        if (const bbcoop::Team* team = PlayedBy(world.id(), nullptr)) {
            out.set_played_by(team->id());
        }
    };
    if (hosted) {
        if (const auto owned = hosted_world_index.find(member);
            owned != hosted_world_index.end()) {
            size_t shown = 0;
            for (const size_t at : owned->second) {
                if (shown >= worlds_per_player) {
                    break;
                }
                // Indices are rebuilt after every world mutation and sorting.
                publish_world(worlds[at]);
                ++shown;
            }
        }
    } else {
        for (const bbcoop::TeamWorldInfo& world : worlds) {
            publish_world(world); // Preserve original non-Hosted public worlds.
        }
    }"""
OLD_ADD_WORLD = """    worlds.push_back(std::move(world));
    std::ranges::stable_sort(worlds, LaterFirst);
    return true;"""
NEW_ADD_WORLD = """    worlds.push_back(std::move(world));
    std::ranges::stable_sort(worlds, LaterFirst);
    Changed(); // Sorted indices now reference a different world set.
    return true;"""
OLD_SET_WORLDS = """void TeamLobby::SetWorlds(std::vector<bbcoop::TeamWorldInfo> list) {
    worlds = std::move(list);
    std::ranges::stable_sort(worlds, LaterFirst);
}"""
NEW_SET_WORLDS = """void TeamLobby::SetWorlds(std::vector<bbcoop::TeamWorldInfo> list) {
    worlds = std::move(list);
    std::ranges::stable_sort(worlds, LaterFirst);
    Changed(); // Restore may occur after index generation.
}"""
OLD_TAKE_IDLE = """    for (auto& [id, player] : players) {
        if (std::ranges::any_of(taken, [&](const auto& w) { return w.id() == player.world; })) {
            player.world.clear();
        }
    }
    return taken;"""
NEW_TAKE_IDLE = """    for (auto& [id, player] : players) {
        if (std::ranges::any_of(taken, [&](const auto& w) { return w.id() == player.world; })) {
            player.world.clear();
        }
    }
    if (!taken.empty()) {
        Changed(); // Eviction invalidates cached sorted indices.
    }
    return taken;"""
OLD_NOTE_WORLD = """    if (note.played_ms() != 0 && world->played_ms() != note.played_ms()) {
        world->set_played_ms(note.played_ms());
        std::ranges::stable_sort(worlds, LaterFirst);
        changed = true;
    }
    return changed;
}"""
NEW_NOTE_WORLD = """    if (note.played_ms() != 0 && world->played_ms() != note.played_ms()) {
        world->set_played_ms(note.played_ms());
        std::ranges::stable_sort(worlds, LaterFirst);
        changed = true;
    }
    if (changed) {
        Changed(); // NoteWorld can re-sort outside Request().
    }
    return changed;
}"""
NEW_CPP_TEST = """// Hosted world index must stay private and fresh after world-list replacement.
int HostedWorldIndexKeepsFortyPartiesPrivateAfterRestoreAndUpdate() {
  TeamLobby lobby = NewLobby();
  lobby.SetHosted(3, 16);
  for (int pair = 0; pair < 40; ++pair) {
    const std::string a = "a" + std::to_string(pair);
    const std::string b = "b" + std::to_string(pair);
    lobby.Arrive(a, a, false);
    lobby.Arrive(b, b, false);
    CHECK(!PlayAWorld(lobby, a, b).empty());
  }
  CHECK(lobby.Worlds().size() == 40);
  for (int pair = 0; pair < 40; ++pair) {
    const std::string a = "a" + std::to_string(pair);
    const std::string b = "b" + std::to_string(pair);
    const auto own = lobby.StateFor(a);
    CHECK(own.worlds_size() == 1 && own.worlds(0).members_size() == 0);
    CHECK(own.worlds(0).played_by() == lobby.TeamOf(a)->id());
    CHECK(lobby.StateFor(b).worlds_size() == 1);
  }
  lobby.Arrive("uninvited", "Uninvited", false);
  CHECK(lobby.StateFor("uninvited").worlds_size() == 0);
  auto original_worlds = lobby.Worlds();
  lobby.SetWorlds({});
  CHECK(lobby.StateFor("a0").worlds_size() == 0);
  lobby.SetWorlds(original_worlds);
  CHECK(lobby.StateFor("a0").worlds_size() == 1);
  const std::string own_id = lobby.StateFor("a0").worlds(0).id();
  bbcoop::TeamWorldInfo note;
  note.set_id(own_id);
  note.set_played_ms(999999999);
  CHECK(lobby.NoteWorld(note));
  CHECK(lobby.StateFor("a0").worlds_size() == 1);
  CHECK(lobby.StateFor("a0").worlds(0).id() == own_id);
  CHECK(lobby.StateFor("a1").worlds_size() == 1);
  CHECK(lobby.StateFor("a1").worlds(0).id() != own_id);
  CHECK(lobby.StateFor("uninvited").worlds_size() == 0);
  return 0;
}

"""
OLD_MAIN = """int main() {
  int failed = 0;
  failed |= HostedLargeTeamsKeepRosterBoundedThroughChanges();"""
NEW_MAIN = """int main() {
  int failed = 0;
  failed |= HostedLargeTeamsKeepRosterBoundedThroughChanges();
  failed |= HostedWorldIndexKeepsFortyPartiesPrivateAfterRestoreAndUpdate();"""

def unique(source, old, new, label):
    if source.count(old) != 1:
        raise ValueError("Unexpected original staged C++ source: " + label)
    return source.replace(old, new)

def rewrite(cpp, header, tests):
    if "hosted_world_index" in cpp or "hosted_world_index" in header:
        raise ValueError("World index already applied")
    if "hosted_solo_index" not in cpp or "HostedLargeTeamsKeepRosterBoundedThroughChanges" not in tests:
        raise ValueError("Apply exact Hosted roster source stage first")
    cpp = unique(cpp, OLD_CLEAR, NEW_CLEAR, "cached index invalidation")
    cpp = unique(cpp, OLD_INDEX, NEW_INDEX, "index generation")
    cpp = unique(cpp, OLD_STATE, NEW_STATE, "StateFor world privacy")
    cpp = unique(cpp, OLD_ADD_WORLD, NEW_ADD_WORLD, "AddWorld")
    cpp = unique(cpp, OLD_SET_WORLDS, NEW_SET_WORLDS, "SetWorlds")
    cpp = unique(cpp, OLD_TAKE_IDLE, NEW_TAKE_IDLE, "TakeIdleWorlds")
    cpp = unique(cpp, OLD_NOTE_WORLD, NEW_NOTE_WORLD, "NoteWorld")
    header = unique(header, OLD_FIELDS, NEW_FIELDS, "member world cache")
    tests = unique(tests, OLD_MAIN, NEW_CPP_TEST + NEW_MAIN, "C++ test main")
    return cpp, header, tests

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Only the exact original YT1.3 source can be modified")
    paths = [root / path for path in (CPP, HEADER, TEST)]
    for path, p in zip((CPP, HEADER, TEST), paths):
        if git(root, "rev-parse", "HEAD:" + path) != BLOBS[path]:
            raise ValueError("Official source blob drift: " + path)
        if p.is_symlink() or not git(root, "diff", "--", path):
            raise ValueError("Official Hosted roster stage missing: " + path)
    changed = rewrite(*(p.read_text(encoding="utf-8") for p in paths))
    for p, source in zip(paths, changed):
        p.write_text(source, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_HOSTED_MEMBER_WORLD_INDEX_NATIVE_CPP_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_original_yt130_checkout", type=Path)
    apply(parser.parse_args().disposable_original_yt130_checkout)
