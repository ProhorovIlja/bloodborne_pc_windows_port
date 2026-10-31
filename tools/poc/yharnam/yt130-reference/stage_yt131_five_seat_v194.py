#!/usr/bin/env python3
"""V194: source-locked *server-side* five-seat YT v1.3.1 adaptation.

No live deployment, original game binaries, server databases, packet keys,
or false claim of game client/hostile-role parity. Run only on a disposable
checkout of the published Yharnam Together 1.3.1 source. Preserve official
friends, open team admission, requests and host migration logic.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

from patch_five_hunter_team import FILES, patch

UPSTREAM_131 = "5d2305ee611ef1e03be39ff925f0da75c9a70393"
PINNED_BLOBS = {
    "server/coop/coop.proto": "f0055dce7cb09ff8bd382cff883b588abcf1b4a8",
    "server/coop/team_lobby.h": "10812a30b675e6ffe1292a677ec9cae26d2a2b6b",
    "server/coop/team_lobby.cpp": "3ff6b3add4f7761a544809e85e72b4bdbca09856",
    "server/tests/test_team_lobby.cpp": "08a230342b9449dc228184260dacfd0f9ab36c68",
}
MARK = "SHYT_V194_YT131_OPEN_TEAM_FIVE_SEAT_REGRESSION"
PROTO_GATES = (
    "PROTOCOL_CURRENT = 8;",
    "FRIEND_ADD = 19;",
    "FRIEND_REMOVE = 20;",
    "FRIEND_DECLINE = 21;",
    "SEARCH = 22;",
    "OPEN = 23;",
    "ASK_JOIN = 24;",
    "ASK_CANCEL = 25;",
    "ASK_ACCEPT = 26;",
    "ASK_DECLINE = 27;",
    "RESET_LAMPS = 28;",
    "repeated LobbyPlayer friends = 7;",
    "repeated OpenTeam open_teams = 12;",
    "uint32 team_size = 14;",
)
# Replaces only the existing official v1.3.1 '4 slots full' behavior in
# OpenTeamsAreAskedToJoin. No new network fields or altered authentication.
OLD_OPEN = """  CHECK(lobby.TeamOf("a")->members_size() == 4);
  CHECK(lobby.StateFor("e").open_teams_size() == 0);
  CHECK(
      !lobby.Request("e", Request(Action::ASK_JOIN, {}, team)).notice.empty());
  lobby.Request("d", Request(Action::LEAVE));
  lobby.Request("e", Request(Action::ASK_JOIN, {}, team));"""
NEW_OPEN = """  // SHYT_V194_YT131_OPEN_TEAM_FIVE_SEAT_REGRESSION:
  // At four members ASK stays visible; the fifth can ask and be accepted.
  CHECK(lobby.TeamOf("a")->members_size() == 4);
  CHECK(lobby.StateFor("e").team_size() == 5);
  CHECK(lobby.StateFor("e").open_teams_size() == 1);
  CHECK(lobby.Request("e", Request(Action::ASK_JOIN, {}, team)).changed);
  CHECK(lobby.Request("a", Request(Action::ASK_ACCEPT, "e")).changed);
  CHECK(lobby.TeamOf("a")->members_size() == 5);
  // A SIXTH player cannot see/join this full team, even when ASK is public.
  lobby.Arrive("g", "Gee", false);
  CHECK(lobby.StateFor("g").open_teams_size() == 0);
  CHECK(
      !lobby.Request("g", Request(Action::ASK_JOIN, {}, team)).notice.empty());
  // Leaving releases a real slot; invitation and ASK must still work.
  CHECK(lobby.Request("e", Request(Action::LEAVE)).changed);
  lobby.Request("d", Request(Action::LEAVE));
  lobby.Request("e", Request(Action::ASK_JOIN, {}, team));"""

# Distinct OPEN-mode exercise, not just ASK and old code/invite pathways.
EXTRA_TEST = """
// SHYT_V194_YT131_OPEN_TEAM_FIVE_SEAT_REGRESSION: actual original TeamLobby.
int FiveSeatPublicOpenTeamHonorsServerCapacity() {
  TeamLobby lobby = NewLobby();
  for (const char *m : {"a", "b", "c", "d", "e", "f"}) {
    lobby.Arrive(m, m, false);
  }
  CHECK(lobby.Request("a", Request(Action::CREATE)).changed);
  const std::string team = lobby.TeamOf("a")->id();
  bbcoop::TeamRequest open = Request(Action::OPEN);
  open.set_join(bbcoop::Team::OPEN);
  CHECK(lobby.Request("a", open).changed);
  for (const char* m : {"b", "c", "d", "e"}) {
    CHECK(lobby.StateFor(m).team_size() == 5);
    CHECK(lobby.Request(m, Request(Action::ASK_JOIN, {}, team)).changed);
    CHECK(lobby.TeamOf(m) == lobby.TeamOf("a"));
  }
  CHECK(lobby.TeamOf("a")->members_size() == 5);
  CHECK(SignOf(lobby, "b") == 7 && SignOf(lobby, "c") == 6 &&
        SignOf(lobby, "d") == 5 && SignOf(lobby, "e") == 4);
  CHECK(lobby.StateFor("f").open_teams_size() == 0);
  CHECK(!lobby.Request("f", Request(Action::ASK_JOIN, {}, team)).notice.empty());
  CHECK(!lobby.TeamOf("f"));
  CHECK(lobby.Request("e", Request(Action::LEAVE)).changed);
  CHECK(lobby.Request("f", Request(Action::ASK_JOIN, {}, team)).changed);
  CHECK(lobby.TeamOf("a")->members_size() == 5);
  CHECK(SignOf(lobby, "f") == 4);
  CHECK(SignOf(lobby, "b") == 7 && SignOf(lobby, "c") == 6 &&
        SignOf(lobby, "d") == 5);
  return 0;
}

"""

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def replace_one(text: str, before: str, after: str, label: str) -> str:
    if text.count(before) != 1 or after in text:
        raise ValueError(f"V194 upstream source drift in {label}: {text.count(before)}")
    return text.replace(before, after, 1)


def transform(source: dict[str, str]) -> dict[str, str]:
    """Pure function. All checks and modifications before ANY disk write."""
    if set(source) != set(PINNED_BLOBS):
        raise ValueError("V194 incomplete 1.3.1 Qt source registry")
    proto = source["server/coop/coop.proto"]
    for token in PROTO_GATES:
        if proto.count(token) != 1:
            raise ValueError("V194 proto gate missing or duplicate: " + token)
    if MARK in "".join(source.values()):
        raise ValueError("V194 already applied")
    result = patch({name: source[name] for name in FILES})
    if set(result) != set(FILES):
        raise ValueError("V194 inherited V130 five-hunter patch incomplete")
    test_path = "server/tests/test_team_lobby.cpp"
    test = result[test_path]
    test = replace_one(test, OLD_OPEN, NEW_OPEN, "YT131 ASK join/full team")
    test = replace_one(test, "int main() {", EXTRA_TEST + "int main() {",
                       "YT131 original Qt native test main")
    test = replace_one(test, "  failed |= OpenTeamsAreAskedToJoin();",
                       "  failed |= OpenTeamsAreAskedToJoin();\n"
                       "  failed |= FiveSeatPublicOpenTeamHonorsServerCapacity();",
                       "YT131 OPEN-mode real Qt regression invocation")
    result[test_path] = test
    if "constexpr size_t TeamSize = 5;" not in result["server/coop/team_lobby.h"]:
        raise ValueError("V194 server team max not applied")
    if "std::array<u32, 4> GuestSigns{7, 6, 5, 4}" not in result["server/coop/team_lobby.cpp"]:
        raise ValueError("V194 server four remote slot signs not applied")
    return result


def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("V194 expects disposable checkout directory")
    rev = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                  text=True, stderr=subprocess.DEVNULL).strip()
    if rev != UPSTREAM_131:
        raise ValueError("V194 requires exact released YT 1.3.1 checkout")
    originals: dict[str, str] = {}
    for name, digest in PINNED_BLOBS.items():
        target = root / name
        if not target.is_file() or target.is_symlink():
            raise ValueError("V194 original upstream source missing or linked: " + name)
        raw = target.read_bytes()
        if git_blob(raw) != digest:
            raise ValueError("V194 upstream C++/protobuf blob mismatch: " + name)
        originals[name] = raw.decode("utf-8")
    staged = transform(originals)
    # Never mutate proto. Keep official friends/open/ASK schema byte-for-byte.
    assert "server/coop/coop.proto" not in staged
    for name, text in staged.items():
        (root / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_V194_YT131_FIVE_HUNTER_OPEN_ASK_SERVER_SOURCE_STAGED_ONLY")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_yt131_five_seat_v194.py DISPOSABLE_YT131")
    stage(Path(sys.argv[1]))
