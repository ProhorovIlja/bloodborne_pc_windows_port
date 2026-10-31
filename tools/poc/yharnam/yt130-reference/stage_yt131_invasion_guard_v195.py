#!/usr/bin/env python3
"""V195: guarded, ONE-invader YT 1.3.1 five-seat Qt admission migration.

Reuses an exact source-pinned V194 TeamLobby already staged into a disposable
copy of the published 1.3.1 tree. Keeps host invasion opt-in OFF by default.
This protects capacity, timing and guest sign allocation, but does NOT promise
3 concurrent invaders or retail Bloodborne hostile kind/sign correctness.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys

PIN = "5d2305ee611ef1e03be39ff925f0da75c9a70393"
INV = "server/coop/invasions.h"
WORLD = "server/src/bloodborne_world.cpp"
TEST = "server/tests/test_invasions.cpp"
FILES = (INV, WORLD, TEST)
BLOBS = {
    INV: "4c3441dfefd1913966b7d715622389b48960364a",
    WORLD: "3a28d826d52870fbaed2b8bf9a37aac51dd3cc45",
    TEST: "2ce89d835c0ac9301fa4366a3068ef4864ef5a6c",
}
MARK = "SHYT_V195_YT131_FIVE_SEAT_INVASION_RECHECK"

def git_blob(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def one(s: str, a: str, b: str, why: str) -> str:
    n = s.count(a)
    if n != 1 or b in s:
        raise ValueError("V195 original C++ source drift in " + why + f": {n} anchors")
    return s.replace(a, b, 1)

def patch(source: dict[str, str]) -> dict[str, str]:
    if set(source) != set(FILES):
        raise ValueError("V195 original source registry incomplete")
    h, w, t = (source[p] for p in FILES)
    if any(MARK in text for text in source.values()):
        raise ValueError("V195 already applied")
    h = one(h,
        "// The game's player slots (the host and three): an invader needs a free one, so a session of\n"
        "// this many is never invaded.\n"
        "constexpr size_t InvasionMaxPlayers = 4;",
        "// " + MARK + ": five total bodies, co-op + invaders combined.\n"
        "// Only ONE hostile is actually supported by the unmodified YT 1.3.1\n"
        "// game/session service; 2+3 still needs the separate V108 redesign.\n"
        "constexpr size_t InvasionMaxPlayers = 5;\n"
        "constexpr size_t ImplementedInvadersPerWorld = 1;\n"
        "constexpr bool FitsFiveSeatRoles(size_t coop, size_t hostile) noexcept {\n"
        "    return coop > 0 && coop <= 5 && hostile <= 3 && hostile <= 5 - coop;\n"
        "}\n"
        "constexpr bool SupportsCurrentServerInvasion(size_t coop, size_t hostile) noexcept {\n"
        "    return FitsFiveSeatRoles(coop, hostile) && hostile <= ImplementedInvadersPerWorld;\n"
        "}\n"
        "static_assert(FitsFiveSeatRoles(5, 0));\n"
        "static_assert(FitsFiveSeatRoles(4, 1));\n"
        "static_assert(FitsFiveSeatRoles(3, 2)); // intended; NOT YET implemented\n"
        "static_assert(FitsFiveSeatRoles(2, 3)); // intended; NOT YET implemented\n"
        "static_assert(!FitsFiveSeatRoles(5, 1));\n"
        "static_assert(!FitsFiveSeatRoles(4, 2));\n"
        "static_assert(SupportsCurrentServerInvasion(4, 1));\n"
        "static_assert(!SupportsCurrentServerInvasion(3, 2));",
        "five-body, one-hostile role policy")
    old_target = """    for (const auto& [key, member] : members) {
        if (member.party == world.name && !member.hostile) {
            ++target.players;
            target.members.push_back({member.map, member.level, member.boss});
        }
    }
    return target;
}"""
    new_target = """    for (const auto& [key, member] : members) {
        if (member.party == world.name && !member.hostile) {
            ++target.players;
            target.members.push_back({member.map, member.level, member.boss});
        }
    }
    // """ + MARK + """: reserve ALL lobby members, even offline/not
    // yet joined to the actual room. Never match a 6th body during a
    // loading/reconnect window in a full five-hunter team.
    if (world.session) {
        if (const bbcoop::Team* team = lobby.TeamOf(world.session->host())) {
            target.players = std::max(target.players,
                                      static_cast<size_t>(team->members_size()));
        }
    }
    return target;
}"""
    w = one(w, old_target, new_target, "reserved co-op seats at match")
    old_start = """    Member& invader = found->second;
    invader.visiting = world.name;
    invader.hostile = true;
    invasion.joined = true;
    invasion.joined_ms = now_ms;
    // Its slot byte: the configured one, or the first free below the guests' 7/6/5.
    std::set<std::uint32_t> taken;
    if (const bbcoop::Team* team = lobby.TeamOf(world.session->host())) {
        for (const bbcoop::TeamMember& m : team->members()) {
            taken.insert(m.sign());
        }
    }
    std::uint32_t sign = invasion_rules.sign;
    for (std::uint32_t free = 4; taken.contains(sign) && free > 0; --free) {
        sign = free;
    }
    bbcoop::Envelope start;"""
    new_start = """    // """ + MARK + """: the invasion notice was sent 10 seconds
    // ago. Revalidate the CURRENT room, authority, host consent, boss and
    // reserved member slots before allowing hostile state or routing.
    const bbcoop::Team* team = lobby.TeamOf(world.session->host());
    const InvasionTarget live = TargetOf(world);
    if (!team || !live.session_open || !live.allows_invaders ||
        !SupportsCurrentServerInvasion(live.players, 1) ||
        std::ranges::any_of(live.members, [](const auto& m) { return m.boss; })) {
        EndInvasion(world.name, bbcoop::InvasionEnd::REFUSED, now_ms, result);
        return;
    }
    std::set<std::uint32_t> taken;
    for (const bbcoop::TeamMember& m : team->members()) {
        taken.insert(m.sign());
    }
    const auto available = [&](std::uint32_t candidate) {
        return candidate >= 4 && candidate <= 7 && !taken.contains(candidate);
    };
    std::uint32_t sign = available(invasion_rules.sign) ? invasion_rules.sign : 0;
    for (const std::uint32_t candidate : {4u, 5u, 6u, 7u}) {
        if (!sign && available(candidate)) sign = candidate;
    }
    if (!sign) {
        EndInvasion(world.name, bbcoop::InvasionEnd::REFUSED, now_ms, result);
        return;
    }
    Member& invader = found->second;
    invader.visiting = world.name;
    invader.hostile = true;
    invasion.joined = true;
    invasion.joined_ms = now_ms;
    bbcoop::Envelope start;"""
    w = one(w, old_start, new_start, "10s delayed hostile join recheck")
    old_changed = """    if (outcome.changed) {
        StoreWorldList(result);
    }
    // Invasions: the leader turned them off: a running one ends."""
    new_changed = """    if (outcome.changed) {
        StoreWorldList(result);
        // """ + MARK + """: another cooperator can fill the last
        // slot AFTER a hostile was matched. Revoke the hostile session
        // immediately; 5 co-op + 1 hostile must never coexist.
        if (const bbcoop::Team* team = lobby.TeamOf(member.lobby);
            team && team->members_size() >= static_cast<int>(InvasionMaxPlayers) &&
            !team->party().empty()) {
            const QString party = FolderOf(QByteArray::fromStdString(team->party()));
            if (invasions.contains(party)) {
                EndInvasion(party, bbcoop::InvasionEnd::REFUSED, now_ms, result);
            }
        }
    }
    // Invasions: the leader turned them off: a running one ends."""
    w = one(w, old_changed, new_changed, "new fifth team member drops hostile")
    probe = """
// SHYT_V195_YT131_FIVE_SEAT_INVASION_RECHECK: original compiled C++ policy.
int FifthSeatInvaderCapacityAndOptIn() {
  InvasionTarget target = Open();
  target.players = 4;
  CHECK(SupportsCurrentServerInvasion(4, 1));
  CHECK(May(target));  // four co-operators plus one opt-in hostile
  target.players = 5;
  CHECK(!May(target)); // no sixth body
  target.players = 4;
  target.allows_invaders = false;
  CHECK(!May(target));
  target.allows_invaders = true;
  target.session_open = false;
  CHECK(!May(target));
  CHECK(!SupportsCurrentServerInvasion(3, 2)); // separate V108 work
  CHECK(!SupportsCurrentServerInvasion(2, 3));
  CHECK(FitsFiveSeatRoles(3, 2)); // desired total-seats policy
  CHECK(FitsFiveSeatRoles(2, 3));
  CHECK(!FitsFiveSeatRoles(5, 1));
  return 0;
}

"""
    t = one(t, "} // namespace\n\nint main() {",
            probe + "} // namespace\n\nint main() {",
            "original native invasion test insertion")
    t = one(t,
        '      {"AFullSessionHasNoSlotForAnInvader", AFullSessionHasNoSlotForAnInvader},',
        '      {"AFullSessionHasNoSlotForAnInvader", AFullSessionHasNoSlotForAnInvader},\n'
        '      {"FifthSeatInvaderCapacityAndOptIn", FifthSeatInvaderCapacityAndOptIn},',
        "original native invasion test execution")
    return dict(zip(FILES, (h, w, t)))

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                               text=True, stderr=subprocess.DEVNULL).strip() != PIN:
        raise ValueError("V195 requires exact disposable YT 1.3.1 checkout")
    # Five-seat TeamLobby is staged from V194 first; reject 4-seat games.
    team = root / "server/coop/team_lobby.h"
    test = root / "server/tests/test_team_lobby.cpp"
    if any(not p.is_file() or p.is_symlink() for p in (team, test)):
        raise ValueError("V195 prerequisite TeamLobby sources missing")
    if ("constexpr size_t TeamSize = 5;" not in team.read_text(encoding="utf-8")
        or "FiveSeatPublicOpenTeamHonorsServerCapacity" not in test.read_text(encoding="utf-8")):
        raise ValueError("V195 requires source-locked V194 five-seat server first")
    original = {}
    for name, digest in BLOBS.items():
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("V195 original C++ source file missing: " + name)
        # Exact pinned Git blobs, not CRLF-mutated checkout content.
        raw = subprocess.check_output(["git", "-C", str(root), "show", "HEAD:" + name])
        if git_blob(raw) != digest:
            raise ValueError("V195 original Git C++ blob SHA drift: " + name)
        work = path.read_bytes()
        if work != raw:
            raise ValueError("V195 original C++ working tree changed or CRLF: " + name)
        original[name] = raw.decode("utf-8")
    changed = patch(original)
    for name, text in changed.items():
        (root / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_V195_YT131_ORIGINAL_SINGLE_INVADER_4_PLUS_1_SAFE_SOURCE_STAGE")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_yt131_invasion_guard_v195.py DISPOSABLE_YT131_V194")
    stage(Path(sys.argv[1]))
