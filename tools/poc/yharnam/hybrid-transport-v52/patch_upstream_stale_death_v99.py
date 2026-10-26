#!/usr/bin/env python3
"""V99: backport Kaniel PR413, with map visit and handle+pointer safety.

Revived guest bodies on the host retain AI info+0x18 bit0. Bosses ignore
the guest until someone else loads a map. Wait three seconds of the same
living, non-invader, non-downed body, then clear the stale bit. This is
original native game memory; no gameplay UDP or shadNet wire changes.
"""
PARTY_H="emulator/src/core/bloodborne_party.h"
PARTY_CPP="emulator/src/core/bloodborne_party.cpp"
DEATH_CPP="emulator/src/core/bloodborne_party_death.cpp"
RE_CPP="emulator/src/core/bloodborne_re.cpp"
INTERNAL_H="emulator/src/core/bloodborne_re_internal.h"
FILES=(PARTY_H,PARTY_CPP,DEATH_CPP,RE_CPP,INTERNAL_H)
TAG="SHYT-V99-REVIVED-AI-TARGET"

def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise ValueError(f"V99 original pinned {label} drift: {n}")
    return s.replace(old,new,1)

def patch(files):
    data={}
    for name in FILES:
        if name not in files:raise ValueError("V99 missing native source "+name)
        data[name]=files[name].decode("utf-8")
        if TAG in data[name]:raise ValueError("V99 already applied")
    data[PARTY_H]=one(data[PARTY_H],
        '''std::string TargetCandidateBlock(const TargetCandidate& candidate);
// Where the board has the other members down on''',
        '''std::string TargetCandidateBlock(const TargetCandidate& candidate);
// SHYT-V99-REVIVED-AI-TARGET: source-proven Kaniel PR413, hardened for
// a changing world visit and reused game character handle/info address.
class StaleDeathMarks {
public:
    static constexpr s64 HoldMs=3000;
    struct Body {
        u32 handle=0;
        u64 info=0;
        bool marked=false;
        bool dead=false;
        bool downed=false;
        bool invader=false;
    };
    std::vector<u32> Tick(std::span<const Body> bodies,s64 now_ms,u64 visit);
private:
    struct Seen {u32 handle;u64 info;s64 since;};
    std::vector<Seen> pending;
    u64 last_visit=0;
};
// Where the board has the other members down on''',
        "per-guest proof class")
    data[PARTY_CPP]=one(data[PARTY_CPP],
        '''    if (candidate.has_info && (candidate.info_d & 0x10) != 0) {
        return "info 0xd bit 0x10";
    }
    return "";
}

std::vector<LampPosition> OthersDownOnMap''',
        '''    if (candidate.has_info && (candidate.info_d & 0x10) != 0) {
        return "info 0xd bit 0x10";
    }
    if (candidate.has_info && (candidate.info_18 & 1) != 0)
        return "marked dead (info 0x18 bit 0)";
    return "";
}

// SHYT-V99-REVIVED-AI-TARGET: never carry proof to another map visit.
std::vector<u32> StaleDeathMarks::Tick(
    std::span<const Body> bodies,s64 now_ms,u64 visit) {
    if(!visit || (last_visit && last_visit!=visit)) {
        pending.clear();
        last_visit=visit;
        if(!visit)return {};
    }
    last_visit=visit;
    std::vector<u32> clear;
    std::vector<Seen> keep;
    for(const Body& body:bodies) {
        if(!body.handle || body.info<0x10000 || !body.marked ||
           body.dead || body.downed || body.invader)continue;
        const auto it=std::ranges::find_if(
            pending,[&](const Seen& p) {
                return p.handle==body.handle && p.info==body.info;
            });
        const s64 since=it==pending.end()?now_ms:it->since;
        if(now_ms<since)continue;
        if(now_ms-since>=HoldMs)clear.push_back(body.handle);
        else keep.push_back(Seen{body.handle,body.info,since});
    }
    pending=std::move(keep);
    return clear;
}

std::vector<LampPosition> OthersDownOnMap''',
        "original AI target classifier and policy")
    data[INTERNAL_H]=one(data[INTERNAL_H],
        '''void LogEnemyTargets();
void LogJoinTasksOnChange();''',
        '''void LogEnemyTargets();
void ClearStaleDeathMarks(); // SHYT-V99-REVIVED-AI-TARGET
void LogJoinTasksOnChange();''',
        "native game tick declaration")
    data[RE_CPP]=one(data[RE_CPP],
        '''        LogUnsharedNearbyCharacters();
    }
    LogOtherPlayersChanges();''',
        '''        LogUnsharedNearbyCharacters();
    }
    ClearStaleDeathMarks(); // SHYT-V99-REVIVED-AI-TARGET, clear on exit too
    LogOtherPlayersChanges();''',
        "original game tick integration")
    data[DEATH_CPP]=one(data[DEATH_CPP],
        '''} // namespace Coop

} // namespace Core::Bloodborne
''',
        '''// SHYT-V99-REVIVED-AI-TARGET. Only the original game thread may
// clear this internal AI flag; a network message cannot trigger it.
void ClearStaleDeathMarks() {
    static StaleDeathMarks marks;
    const u64 visit=CurrentPlace().visit;
    const s64 now=SteadyMilliseconds();
    if(!InPartyHere()) {
        (void)marks.Tick({},now,0);
        return;
    }
    const std::vector<OtherPlayer> players=OtherPlayers();
    const std::vector<u32> invaders=InvaderHandles();
    std::vector<StaleDeathMarks::Body> bodies;
    for(const OtherPlayer& other:players) {
        if(other.character<0x10000 ||
           !HasMemoryAccess(other.character+0x18,8,MemoryProt::CpuRead))
            continue;
        const u64 control=ReadValue<u64>(other.character,0x18);
        if(control<0x10000 ||
           !HasMemoryAccess(control+0x30,8,MemoryProt::CpuRead))
            continue;
        const u64 info=ReadValue<u64>(control,0x30);
        if(info<0x10000 ||
           !HasMemoryAccess(info+0x18,1,MemoryProt::CpuWrite))
            continue;
        const u32 handle=ReadValue<u32>(other.character,0x08);
        bodies.push_back({
            .handle=handle,.info=info,
            .marked=(ReadValue<u8>(info,0x18)&1)!=0,
            .dead=(other.dead_flags&0x05)!=0,
            .downed=ReadValue<s32>(other.character,CharacterTeamOffset)
                        ==DownedTeams::Hostile,
            .invader=std::ranges::find(invaders,handle)!=invaders.end()
        });
    }
    for(const u32 handle:marks.Tick(bodies,now,visit)) {
        const auto found=std::ranges::find(
            bodies,handle,&StaleDeathMarks::Body::handle);
        if(found==bodies.end())continue;
        if(!InPartyHere() || CurrentPlace().visit!=visit ||
           std::ranges::find(invaders,handle)!=invaders.end())continue;
        // Recheck current target, object identity, state and access right
        // before write. A recycled handle cannot inherit the old proof.
        bool still_living=false;
        for(const OtherPlayer& p:players) {
            if(p.character<0x10000 || (p.dead_flags&0x05)!=0 ||
               !HasMemoryAccess(p.character+0x18,8,MemoryProt::CpuRead))
                continue;
            const u64 control=ReadValue<u64>(p.character,0x18);
            if(control<0x10000 ||
               !HasMemoryAccess(control+0x30,8,MemoryProt::CpuRead) ||
               ReadValue<u64>(control,0x30)!=found->info ||
               ReadValue<u32>(p.character,0x08)!=handle ||
               ReadValue<s32>(p.character,CharacterTeamOffset)
                   ==DownedTeams::Hostile)continue;
            still_living=true;
            break;
        }
        if(!still_living ||
           !HasMemoryAccess(found->info+0x18,1,MemoryProt::CpuWrite))
            continue;
        const u8 bits=ReadValue<u8>(found->info,0x18);
        if((bits&1)==0)continue;
        WriteValue(found->info,0x18,static_cast<u8>(bits&~u8{1}));
        LOG_INFO(Debug,
           "Bloodborne party: revived teammate {:#x} is now a boss AI "
           "target again on map {:#x}",handle,CurrentPlace().map);
    }
}

} // namespace Coop

} // namespace Core::Bloodborne
''',
        "end of original game enemy target module")
    return {key:value.encode("utf-8") for key,value in data.items()}
