#!/usr/bin/env python3
"""Real original YT1.3 native game: per-ID simultaneous hostile invasion state.

This is a native game source patch, not an overlay mock. The original
InvadedTeam class has ONE id/name/phase; another InvaderJoined replaces it and
an unrelated End destroys its HUD and hostile lifetime. Use a bounded three-
hostile ledger. The invader's own InvaderTrip remains one outgoing trip.

Five total active game bodies and server-authenticated slots are owned by
the game/server admission layer, NOT this UI/presentation ledger. This patch
does not claim hostile kind/signs work until original game live capture.
"""
from __future__ import annotations
from pathlib import Path

HEADER="emulator/src/core/bloodborne_invasion.h"
CPP="emulator/src/core/bloodborne_invasion.cpp"
TEST="emulator/tests/bloodborne/test_bloodborne_invasion.cpp"
FILES=(HEADER,CPP,TEST)
TAG="SHYT-V107-MULTI-HOSTILE-NATIVE-GAME"

def one(s:str,old:str,new:str,label:str)->str:
    n=s.count(old)
    if n!=1:
        raise ValueError(f"{TAG} source drift {label}: {n} anchors")
    return s.replace(old,new,1)

def region(s:str,start:str,end:str,replacement:str,label:str)->str:
    if s.count(start)!=1 or s.count(end)!=1:
        raise ValueError(f"{TAG} region drift {label}")
    a=s.index(start)
    b=s.index(end,a)
    if b<=a:
        raise ValueError(f"{TAG} invalid region {label}")
    return s[:a]+replacement+"\n"+s[b:]

NEW_CLASS = """// SHYT-V107-MULTI-HOSTILE-NATIVE-GAME: original game, up to THREE
// independent hostile visitors. Their IDs/lifecycles NEVER replace each other.
// The invader's own InvaderTrip remains one outgoing trip.
class InvadedTeam {
public:
    enum class Phase { None, Approaching, Invaded, Ended };
    static constexpr s64 EndShownMs = 6'000;
    static constexpr size_t MaxConcurrentHostiles = 3;
    void TakeNotice(const bbcoop::InvasionNotice& notice, s64 now_ms);
    void TakeJoined(const bbcoop::InvaderJoined& joined, s64 now_ms);
    void TakeEnd(const bbcoop::InvasionEnd& end, s64 now_ms);
    void Tick(s64 now_ms);
    Phase Current() const;
    // A selected foreground invader remains for legacy team overlay.
    // The game uses ALL hostile lines for body presence and PvP targeting.
    std::string Invader() const;
    const std::string& Name() const;
    const std::string& Target() const;
    s64 ApproachUntilMs() const;
    bbcoop::InvasionEnd::Reason EndReason() const;
    size_t ActiveCount() const;
    size_t JoinedCount() const;
    std::vector<std::string> Invaders() const;
private:
    struct Visitor {
        Phase phase = Phase::None;
        std::string member, name, target;
        s64 approach_until_ms = 0;
        s64 ended_ms = 0;
        bbcoop::InvasionEnd::Reason end_reason = bbcoop::InvasionEnd::NONE;
    };
    const Visitor* Foreground() const;
    std::map<u64,Visitor> visitors; // keyed by server-issued Invasion ID
};

"""

NEW_METHODS = """// SHYT-V107-MULTI-HOSTILE-NATIVE-GAME: one game-side record per
// server-issued, nonzero invasion ID. A duplicate or reordered notice
// NEVER rewinds an already spawned hostile back to a countdown.
size_t InvadedTeam::ActiveCount() const {
    return static_cast<size_t>(std::ranges::count_if(visitors, [](const auto& item) {
        return item.second.phase == Phase::Approaching ||
               item.second.phase == Phase::Invaded;
    }));
}

size_t InvadedTeam::JoinedCount() const {
    return static_cast<size_t>(std::ranges::count_if(visitors, [](const auto& item) {
        return item.second.phase == Phase::Invaded;
    }));
}

std::vector<std::string> InvadedTeam::Invaders() const {
    std::vector<std::string> out;
    for (const auto& [id, visitor] : visitors) {
        if (visitor.phase == Phase::Invaded)
            out.push_back(visitor.member);
    }
    return out;
}

const InvadedTeam::Visitor* InvadedTeam::Foreground() const {
    for (const auto& [id, visitor] : visitors) {
        if (visitor.phase == Phase::Invaded) return &visitor;
    }
    for (const auto& [id, visitor] : visitors) {
        if (visitor.phase == Phase::Approaching) return &visitor;
    }
    for (const auto& [id, visitor] : visitors) {
        if (visitor.phase == Phase::Ended) return &visitor;
    }
    return nullptr;
}

InvadedTeam::Phase InvadedTeam::Current() const {
    const Visitor* current = Foreground();
    return current ? current->phase : Phase::None;
}

std::string InvadedTeam::Invader() const {
    const Visitor* current = Foreground();
    return current && current->phase == Phase::Invaded ?
           current->member : std::string{};
}

const std::string& InvadedTeam::Name() const {
    static const std::string empty;
    const Visitor* current = Foreground();
    return current ? current->name : empty;
}

const std::string& InvadedTeam::Target() const {
    static const std::string empty;
    const Visitor* current = Foreground();
    return current ? current->target : empty;
}

s64 InvadedTeam::ApproachUntilMs() const {
    const Visitor* current = Foreground();
    return current ? current->approach_until_ms : 0;
}

bbcoop::InvasionEnd::Reason InvadedTeam::EndReason() const {
    const Visitor* current = Foreground();
    return current ? current->end_reason : bbcoop::InvasionEnd::NONE;
}

void InvadedTeam::TakeNotice(const bbcoop::InvasionNotice& notice, s64 now_ms) {
    if (!notice.id()) return;
    auto existing = visitors.find(notice.id());
    if (existing == visitors.end() && ActiveCount() >= MaxConcurrentHostiles)
        return; // never a fourth hostile, even after a stale notice
    if (existing != visitors.end() && existing->second.phase != Phase::Approaching)
        return; // already spawned/finished; no resurrection from stale UDP
    Visitor& visitor = visitors[notice.id()];
    visitor.phase = Phase::Approaching;
    visitor.member = notice.invader();
    visitor.target = notice.target();
    visitor.name.clear();
    visitor.approach_until_ms = now_ms + notice.in_ms();
    visitor.end_reason = bbcoop::InvasionEnd::NONE;
}

void InvadedTeam::TakeJoined(const bbcoop::InvaderJoined& joined, s64) {
    if (!joined.id()) return;
    auto existing = visitors.find(joined.id());
    if (existing == visitors.end() && ActiveCount() >= MaxConcurrentHostiles)
        return;
    if (existing != visitors.end() && existing->second.phase == Phase::Ended)
        return; // End happened before this delayed joined event
    Visitor& visitor = visitors[joined.id()];
    visitor.phase = Phase::Invaded;
    visitor.member = joined.member();
    visitor.target = joined.target();
    visitor.name = joined.name().empty() ? joined.member() : joined.name();
    visitor.end_reason = bbcoop::InvasionEnd::NONE;
}

void InvadedTeam::TakeEnd(const bbcoop::InvasionEnd& end, s64 now_ms) {
    if (!end.id()) return; // refused search is not a hosted invasion
    const auto it = visitors.find(end.id());
    if (it == visitors.end() || it->second.phase == Phase::Ended)
        return; // an unrelated hostile's end MUST NOT remove the others
    it->second.phase = Phase::Ended;
    it->second.end_reason = end.reason();
    it->second.ended_ms = now_ms;
}

void InvadedTeam::Tick(s64 now_ms) {
    for (auto it = visitors.begin(); it != visitors.end();) {
        if (it->second.phase == Phase::Ended &&
            now_ms >= it->second.ended_ms &&
            now_ms - it->second.ended_ms >= EndShownMs)
            it = visitors.erase(it);
        else
            ++it;
    }
}

"""

GAME_TEST = """TEST(InvadedTeam, ThreeConcurrentHostilesIndependentIdsAndEnds) {
    InvadedTeam team;
    EXPECT_EQ(team.ActiveCount(), 0u);
    for (u64 id = 11; id <= 13; ++id) {
        auto notice = Notice(id);
        notice.set_invader("enemy-" + std::to_string(id));
        team.TakeNotice(notice, 1000);
    }
    EXPECT_EQ(team.ActiveCount(), 3u);
    auto fourth = Notice(14);
    team.TakeNotice(fourth, 1000);
    EXPECT_EQ(team.ActiveCount(), 3u);
    for (u64 id = 11; id <= 13; ++id) {
        bbcoop::InvaderJoined joined;
        joined.set_id(id);
        joined.set_member("enemy-" + std::to_string(id));
        joined.set_name("Hostile " + std::to_string(id));
        joined.set_target("host");
        team.TakeJoined(joined, 1200);
    }
    EXPECT_EQ(team.JoinedCount(), 3u);
    EXPECT_EQ(team.Invaders().size(), 3u);
    team.TakeNotice(Notice(12), 1400); // delayed notice cannot unwind join
    EXPECT_EQ(team.JoinedCount(), 3u);
    team.TakeEnd(End(12, bbcoop::InvasionEnd::INVADER_DIED), 1500);
    EXPECT_EQ(team.JoinedCount(), 2u);
    EXPECT_EQ(team.ActiveCount(), 2u);
    EXPECT_EQ(team.Invaders().size(), 2u);
    team.TakeJoined(bbcoop::InvaderJoined{}, 1600); // invalid id, no revive
    team.TakeEnd(End(17, bbcoop::InvasionEnd::HOST_LEFT), 1600);
    EXPECT_EQ(team.JoinedCount(), 2u);
    team.TakeNotice(Notice(12), 1700); // cannot resurrect terminated id
    EXPECT_EQ(team.ActiveCount(), 2u);
    team.TakeNotice(Notice(14), 1800); // freed third space
    EXPECT_EQ(team.ActiveCount(), 3u);
    team.Tick(1500 + InvadedTeam::EndShownMs);
    team.TakeEnd(End(11, bbcoop::InvasionEnd::HOST_LEFT), 8000);
    team.TakeEnd(End(13, bbcoop::InvasionEnd::INVADER_LEFT), 8001);
    team.TakeEnd(End(14, bbcoop::InvasionEnd::INVADERS_OFF), 8002);
    EXPECT_EQ(team.ActiveCount(), 0u);
    team.Tick(8002 + InvadedTeam::EndShownMs);
    EXPECT_EQ(team.Current(), InvadedTeam::Phase::None);
}

"""

def patch(sources:dict[str,str])->dict[str,str]:
    if set(sources)!=set(FILES):
        raise ValueError(TAG+" requires exact native header, source and test")
    h,cpp,test=(sources[p] for p in FILES)
    if TAG in h or TAG in cpp or TAG in test:
        raise ValueError(TAG+" installed twice")
    h=one(h,'#include <optional>','#include <map>\n#include <optional>',"std::map")
    h=region(h,'class InvadedTeam {','// What the overlay\'s invasion notice shows',
             NEW_CLASS,"original InvadedTeam C++ class")
    cpp=region(cpp,'void InvadedTeam::TakeNotice(', 'InvasionView InvasionViewOf(',
               NEW_METHODS,"original InvadedTeam C++ methods")
    test=one(test,
       'TEST(InvadedTeam, NoticeJoinedEnd) {',
       GAME_TEST+'TEST(InvadedTeam, NoticeJoinedEnd) {',
       "real original game gtest insertion")
    return dict(zip(FILES,(h,cpp,test)))

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    original={}
    for name in FILES:
        file=root/name
        if not file.is_file() or file.is_symlink():
            raise ValueError(TAG+" missing original native client file: "+name)
        original[name]=file.read_text("utf-8")
    changes=patch(original)
    for name,body in changes.items():
        (root/name).write_text(body,encoding="utf-8")

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:
        raise SystemExit("usage: patch_original_multi_invader_client_v107.py PINNED_YT_130_SOURCE")
    stage(Path(sys.argv[1]))
    print("SHYT_V107_NATIVE_ORIGINAL_GAME_3_HOSTILES_STAGED")
