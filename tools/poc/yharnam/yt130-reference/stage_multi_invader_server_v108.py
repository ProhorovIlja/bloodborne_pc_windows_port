#!/usr/bin/env python3
"""V108: real YT1.3 Qt server multi-invader session, under existing PR37.

Runs AFTER stage_five_hunter_invasion_guard.py, on disposable pinned 1.3
source. Mutates ORIGINAL Service, Hub and C++ functional tests, not an
isolated mock. Five total bodies. Allows three independent invader IDs,
distinct reserved signs, per-invader cleanup and direct server link routing.
No production PvP until original native hostile kind/sign captures + game
build + cross-PC tests succeed. Server Invasions and host opt-in remain OFF
by default.
"""
from __future__ import annotations
from pathlib import Path
import sys

HEADER = "server/src/bloodborne_world.h"
CPP = "server/src/bloodborne_world.cpp"
POLICY = "server/coop/invasions.h"
RULES = "server/coop/invasions.cpp"
LINK = "server/src/server_link.cpp"
TEST = "server/tests/test_bloodborne_world.cpp"
FILES = (HEADER, CPP, POLICY, RULES, LINK, TEST)
TAG = "SHYT-V108-MULTI-INVADER-ORIGINAL-SERVER"

def one(s, a, b, label):
    n = s.count(a)
    if n != 1:
        raise ValueError(f"{TAG} source drift {label}: {n} anchors")
    return s.replace(a, b, 1)

def block(s, a, b, new, label):
    if s.count(a) != 1 or s.count(b) != 1:
        raise ValueError(f"{TAG} block drift {label}: {s.count(a)}, {s.count(b)}")
    start=s.index(a); end=s.index(b,start)
    if end <= start: raise ValueError(f"{TAG} block order {label}")
    return s[:start]+new+"\n"+s[end:]

def patch(source):
    if set(source)!=set(FILES):
        raise ValueError(f"{TAG}: exact six original native Qt files required")
    h,cpp,policy,rules,link,test=(source[k] for k in FILES)
    if any(TAG in s for s in (h,cpp,policy,rules,link,test)):
        raise ValueError(f"{TAG}: double application denied")
    if "InvasionMaxPlayers = 5" not in policy or "SupportsCurrentServerInvasion" not in cpp:
        raise ValueError("V108 requires previously verified five-hunter admission guard")

    # Reserve a real seat for every pending invasion. Distinct ID and
    # distinct slot survive the ten-second notice, world-map changes and
    # the arrival of multiple new invaders in the same matcher tick.
    h=one(h,
        "    // Invasions: one invader on its way to (or in) a team world.",
        "    // "+TAG+": independent, ID-scoped pending/active invaders.",
        "Service Invasion ledger")
    h=one(h,
        "        quint64 id = 0;\n        quint64 invader = 0;",
        "        quint64 id = 0;\n        std::uint32_t sign = 0; // reserved game slot, unique in WORLD\n        quint64 invader = 0;",
        "server slot in Invasion")
    h=one(h,
        "    std::map<QString, Invasion> invasions; // by the invaded world",
        "    std::map<QString, std::map<quint64, Invasion>> invasions; // world -> ID -> visitor",
        "per-world per-ID ledger")
    h=block(h,
        "    void EndInvasion(const QString& world,",
        "    // What a team member's vitals end",
        "    void EndInvasion(const QString& world, quint64 invasion_id,\n"
        "                     bbcoop::InvasionEnd::Reason reason, qint64 now_ms, Result& result);\n"
        "    void EndInvasion(const QString& world, bbcoop::InvasionEnd::Reason reason, qint64 now_ms,\n"
        "                      Result& result); // end ALL visitors for boss/wipe/closed session\n",
        "per ID end overload")

    policy=one(policy,
        "constexpr size_t ImplementedInvadersPerWorld = 1;",
        "constexpr size_t ImplementedInvadersPerWorld = 3; // "+TAG,
        "verified concurrent max")
    policy=one(policy,
        "static_assert(!SupportsCurrentServerInvasion(3, 2));",
        "static_assert(SupportsCurrentServerInvasion(3, 2));",
        "three co-op two invaders admission")
    policy=one(policy,
        "static_assert(!SupportsCurrentServerInvasion(2, 3));",
        "static_assert(SupportsCurrentServerInvasion(2, 3));",
        "two co-op three invaders admission")
    policy=one(policy,
        "    bool invaded = false;         // an invader is on its way or in it",
        "    bool invaded = false;         // v1.3 single-invasion compatibility unit tests\n"
        "    size_t invaders = 0;         // "+TAG+": distinct pending+joined visitors",
        "original invasion matching metadata")
    rules=one(rules,
        '    if (target.players >= InvasionMaxPlayers) {\n        return "its session is full";\n    }',
        '    if (target.invaders >= ImplementedInvadersPerWorld ||\n'
        '        target.players >= InvasionMaxPlayers ||\n'
        '        target.invaders > InvasionMaxPlayers - target.players) {\n'
        '        return "its session is full";\n'
        '    }',
        "existing refusal respects all reserved slots")

    # Hub same-team validation precedes Service::RoutesPacket. Treat
    # two hostile visitors to SAME live world as potential peers. Actual
    # GAME packets are still filtered by the strict hostile route table.
    link=one(link,
        "    return (!a_visits.isEmpty() && a_visits == party_of(b)) ||\n"
        "           (!b_visits.isEmpty() && b_visits == party_of(a));",
        "    // "+TAG+": hostile-to-hostile in the same world is allowed\n"
        "    // through this topology gate, never across different worlds.\n"
        "    return (!a_visits.isEmpty() && a_visits == party_of(b)) ||\n"
        "           (!b_visits.isEmpty() && b_visits == party_of(a)) ||\n"
        "           (!a_visits.isEmpty() && a_visits == b_visits);",
        "server link supports peers among hostiles")

    cpp=one(cpp,
        "    // Invasions: the invaded world stays while its invasion runs (the invader itself keeps none).\n"
        "    for (const auto& [name, invasion] : invasions) {\n"
        "        in_use.insert(name);\n"
        "    }",
        "    // "+TAG+": every world with pending or active visitors remains alive.\n"
        "    for (const auto& [name, by_id] : invasions) {\n"
        "        if (!by_id.empty()) in_use.insert(name);\n"
        "    }",
        "world retention")

    cpp=one(cpp,
        "        if (const auto invasion = invasions.find(world.name);\n"
        "            invasion != invasions.end() && invasion->second.joined) {\n"
        "            EndInvasion(world.name, bbcoop::InvasionEnd::PARTY_WIPED, now_ms, result);\n"
        "        }",
        "        if (invasions.contains(world.name)) {\n"
        "            EndInvasion(world.name, bbcoop::InvasionEnd::PARTY_WIPED, now_ms, result);\n"
        "        }",
        "wipe ends all hostile records")

    cpp=block(cpp,
        "    if (const auto invasion = invasions.find(world.name);\n"
        "        invasion != invasions.end() && invasion->second.joined && invasion->second.vitals) {",
        "    return board;\n}",
        "    if (const auto found = invasions.find(world.name); found != invasions.end()) {\n"
        "        for (const auto& [id, invasion] : found->second) {\n"
        "            if (!invasion.joined || !invasion.vitals) continue;\n"
        "            bbcoop::VitalsBoard::Member& line = *board.add_members();\n"
        "            line.set_member(invasion.invader_name);\n"
        "            *line.mutable_vitals() = *invasion.vitals;\n"
        "            line.set_hostile(true);\n"
        "        }\n"
        "    }\n",
        "all hostile vitals lines")

    cpp=one(cpp,
        "    // Invasions: the invader follows the owners too (it travels and sees the enemies by them).\n"
        "    if (const auto invasion = invasions.find(world.name);\n"
        "        invasion != invasions.end() && invasion->second.joined) {\n"
        "        if (const auto invader = members.find(invasion->second.invader); invader != members.end()) {\n"
        "            SendTo(invader->second, envelope, now_ms);\n"
        "        }\n"
        "    }",
        "    // "+TAG+": every active hostile needs the owners for the map it visits.\n"
        "    if (const auto bucket = invasions.find(world.name); bucket != invasions.end()) {\n"
        "        for (const auto& [id, invasion] : bucket->second) {\n"
        "            if (!invasion.joined) continue;\n"
        "            if (const auto invader = members.find(invasion.invader);\n"
        "                invader != members.end()) SendTo(invader->second, envelope, now_ms);\n"
        "        }\n"
        "    }",
        "enemy owners to all hostiles")

    cpp=one(cpp,
        "    std::vector<QString> due;\n"
        "    std::vector<QString> timed_out;\n"
        "    for (const auto& [name, invasion] : invasions) {\n"
        "        if (!invasion.joined && now_ms - invasion.matched_ms >= InvasionNoticeMs) {\n"
        "            due.push_back(name);\n"
        "        } else if (invasion.joined && now_ms - invasion.joined_ms >= InvasionMaxMs) {\n"
        "            timed_out.push_back(name);\n"
        "        }\n"
        "    }\n"
        "    for (const QString& name : due) {\n"
        "        const auto world = worlds.find(name);\n"
        "        if (world == worlds.end()) {\n"
        "            EndInvasion(name, bbcoop::InvasionEnd::HOST_LEFT, now_ms, result);\n"
        "        } else {\n"
        "            JoinInvasion(world->second, invasions.at(name), now_ms, result);\n"
        "        }\n"
        "    }\n"
        "    for (const QString& name : timed_out) {\n"
        "        EndInvasion(name, bbcoop::InvasionEnd::TIMEOUT, now_ms, result);\n"
        "    }",
        "    // "+TAG+": every invasion has its own notice, start, timeout and end.\n"
        "    using Due = std::pair<QString, quint64>;\n"
        "    std::vector<Due> due, timed_out;\n"
        "    for (const auto& [name, bucket] : invasions) {\n"
        "        for (const auto& [id, invasion] : bucket) {\n"
        "            if (!invasion.joined && now_ms - invasion.matched_ms >= InvasionNoticeMs)\n"
        "                due.emplace_back(name,id);\n"
        "            else if (invasion.joined && now_ms - invasion.joined_ms >= InvasionMaxMs)\n"
        "                timed_out.emplace_back(name,id);\n"
        "        }\n"
        "    }\n"
        "    for (const auto& [name,id] : due) {\n"
        "        const auto world = worlds.find(name);\n"
        "        const auto bucket = invasions.find(name);\n"
        "        if (bucket == invasions.end() || !bucket->second.contains(id)) continue;\n"
        "        if (world == worlds.end())\n"
        "            EndInvasion(name,id,bbcoop::InvasionEnd::HOST_LEFT,now_ms,result);\n"
        "        else\n"
        "            JoinInvasion(world->second,bucket->second.at(id),now_ms,result);\n"
        "    }\n"
        "    for (const auto& [name,id] : timed_out)\n"
        "        EndInvasion(name,id,bbcoop::InvasionEnd::TIMEOUT,now_ms,result);",
        "independent per-ID timeouts")

    # Strict hostile-to-hostile route for same WORLD only, never player
    # between two unrelated parties. Hub checks Visits too.
    cpp=one(cpp,
        "    if (from_visitor || to_visitor) {\n"
        "        return BloodborneCoop::RoutesHostilePacket(",
        "    if (sender->second.hostile && target->second.hostile &&\n"
        "        !sender->second.visiting.isEmpty() &&\n"
        "        sender->second.visiting == target->second.visiting) {\n"
        "        return BloodborneCoop::RoutesHostilePacket(\n"
        "            channel,{sender->second.map,target->second.map,\n"
        "                     EnemyPart::None,EnemyPart::None},true);\n"
        "    }\n"
        "    if (from_visitor || to_visitor) {\n"
        "        return BloodborneCoop::RoutesHostilePacket(",
        "hostile-to-hostile route")

    # V107 Qt sends a separate invasion End for each invader. Only
    # the cancelled/dead member is released. Ending boss/host/wipe
    # still closes the entire invaded world in a single world operation.
    cpp=block(cpp,
        "void Service::TakeHostile(Member& member,",
        "BloodborneCoop::InvasionTarget Service::TargetOf(",
        r'''void Service::TakeHostile(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms,
                          Result& result) {
    const QString invaded = InvadedBy(member.key);
    auto world_bucket = invasions.find(invaded);
    auto invasion = world_bucket == invasions.end() ? std::map<quint64, Invasion>::iterator{} :
        std::find_if(world_bucket->second.begin(),world_bucket->second.end(),
          [&](auto& pair) { return pair.second.invader == member.key; });
    switch (envelope.body_case()) {
    case bbcoop::Envelope::kMap:
        member.map = envelope.map().map();
        return;
    case bbcoop::Envelope::kVitals: {
        member.level = envelope.vitals().level();
        if (envelope.vitals().vital() == 3 && !invaded.isEmpty()) {
            if (world_bucket != invasions.end() && invasion != world_bucket->second.end())
                EndInvasion(invaded,invasion->first,bbcoop::InvasionEnd::INVADER_DIED,now_ms,result);
            return;
        }
        if (world_bucket == invasions.end() || invasion == world_bucket->second.end() ||
            !invasion->second.joined) return;
        bbcoop::Vitals line = envelope.vitals();
        line.clear_hits();
        if (!invasion->second.vitals ||
            invasion->second.vitals->SerializeAsString() != line.SerializeAsString()) {
            invasion->second.vitals = std::move(line);
            if (const auto world = worlds.find(invaded); world != worlds.end())
                SendBoards(world->second, PartyBoards::VitalsBoard, now_ms);
        }
        return;
    }
    default: break;
    }
    if (world_bucket != invasions.end() && invasion != world_bucket->second.end() &&
        invasion->second.dropped.insert(static_cast<int>(envelope.body_case())).second) {
        result.log.append(QStringLiteral("invasions: %1 message %2 dropped (hostile cannot alter world)")
            .arg(QString::fromStdString(member.lobby))
            .arg(static_cast<int>(envelope.body_case())));
    }
}
''',
        "per-invader hostile vitals/drops")

    cpp=block(cpp,
        "BloodborneCoop::InvasionTarget Service::TargetOf(",
        "void Service::Match(",
        r'''BloodborneCoop::InvasionTarget Service::TargetOf(const PartyWorld& world) const {
    InvasionTarget target;
    target.world=world.name.toStdString();
    target.invaded=false; // legacy exclusive flag; V108 uses counted invaders
    if (const auto active=invasions.find(world.name); active!=invasions.end())
        target.invaders=active->second.size(); // pending reservations count too
    if (world.session) {
        const bbcoop::Team* team=lobby.TeamOf(world.session->host());
        target.session_open=team && team->started() && !team->party().empty() &&
            FolderOf(QByteArray::fromStdString(team->party()))==world.name;
        target.allows_invaders=target.session_open && team->allow_invaders();
        if (team) target.players=static_cast<size_t>(team->members_size());
    }
    for (const auto& [key, member]:members) {
        if (member.party==world.name && !member.hostile) {
            if (!world.session || !lobby.TeamOf(world.session->host()))
                ++target.players;
            target.members.push_back({member.map,member.level,member.boss});
        }
    }
    return target;
}
''',
        "live world occupancy and reservations")

    cpp=block(cpp,"void Service::Match(","void Service::JoinInvasion(",
        r'''void Service::Match(qint64 now_ms, Result& result) {
    matched_ms=now_ms;
    cooldowns.Expire(now_ms);
    std::vector<InvasionTarget> targets;
    for (const auto& [name,world]:worlds)
        if (world.team && world.session) targets.push_back(TargetOf(world));
    for (auto search=searches.begin();search!=searches.end();) {
        const auto found=members.find(search->first);
        if (found==members.end()) { search=searches.erase(search); continue; }
        Member& invader=found->second;
        if (now_ms-search->second.since_ms>=InvasionSearchMs) {
            Refuse(invader,bbcoop::InvasionEnd::NOT_FOUND,"no world to invade now",now_ms);
            search=searches.erase(search); continue;
        }
        std::vector<InvasionTarget*> open;
        for (auto& target:targets) {
            if (target.world!=invader.party.toStdString() &&
                InvasionRefusal(target,invader.lobby,search->second.level,
                               cooldowns,now_ms).empty())
                open.push_back(&target);
        }
        if (open.empty()) { ++search;continue; }
        InvasionTarget& target=*open[QRandomGenerator::global()->bounded(
            static_cast<quint32>(open.size()))];
        const QString name=QString::fromStdString(target.world);
        const PartyWorld& world=worlds.at(name);
        if (!world.session) { ++search;continue; }
        const bbcoop::Team* team=lobby.TeamOf(world.session->host());
        if (!team || !team->allow_invaders()) { ++search;continue; }
        std::set<std::uint32_t> taken;
        for (const auto& teammate:team->members()) taken.insert(teammate.sign());
        if (const auto used=invasions.find(name);used!=invasions.end())
            for (const auto& [id,active]:used->second) taken.insert(active.sign);
        std::uint32_t sign=0;
        if (invasion_rules.sign>=4 && invasion_rules.sign<=7 &&
            !taken.contains(invasion_rules.sign)) sign=invasion_rules.sign;
        for (std::uint32_t candidate: {4u,5u,6u,7u})
            if (!sign && !taken.contains(candidate)) sign=candidate;
        if (!sign) { ++search;continue; }
        Invasion invasion{};
        invasion.id=++invasions_made;
        invasion.sign=sign;
        invasion.invader=invader.key;
        invasion.invader_name=invader.lobby;
        invasion.target=world.session->host();
        invasion.matched_ms=now_ms;
        invasions[name].emplace(invasion.id,invasion);
        ++target.invaders; // block another match from overbooking this tick
        bbcoop::Envelope notice;
        notice.mutable_invasion_notice()->set_id(invasion.id);
        notice.mutable_invasion_notice()->set_in_ms(
            static_cast<quint32>(InvasionNoticeMs));
        notice.mutable_invasion_notice()->set_invader(invasion.invader_name);
        notice.mutable_invasion_notice()->set_target(invasion.target);
        SendTo(invader,notice,now_ms);
        for (auto& [key,member]:members)
            if (member.party==name && !member.hostile) SendTo(member,notice,now_ms);
        result.log.append(QStringLiteral("invasions: %1 approaches %2, id %3, sign %4")
            .arg(QString::fromStdString(invasion.invader_name),name)
            .arg(invasion.id).arg(sign));
        search=searches.erase(search);
    }
}
''',"multi-invader matcher and atomic sign reservations")

    cpp=block(cpp,"void Service::JoinInvasion(","void Service::EndInvasion(",
        r'''void Service::JoinInvasion(PartyWorld& world, Invasion& invasion, qint64 now_ms,
                           Result& result) {
    const quint64 id=invasion.id;
    const auto found=members.find(invasion.invader);
    if (found==members.end()) {
        EndInvasion(world.name,id,bbcoop::InvasionEnd::INVADER_LEFT,now_ms,result);
        return;
    }
    if (!world.session) {
        EndInvasion(world.name,id,bbcoop::InvasionEnd::HOST_LEFT,now_ms,result);
        return;
    }
    const InvasionTarget live=TargetOf(world);
    const bbcoop::Team* team=lobby.TeamOf(world.session->host());
    if (!team || !live.session_open || !live.allows_invaders ||
        live.invaders>ImplementedInvadersPerWorld ||
        live.players>InvasionMaxPlayers ||
        live.invaders>InvasionMaxPlayers-live.players ||
        std::ranges::any_of(live.members,[](const auto& m){return m.boss;})) {
        EndInvasion(world.name,id,bbcoop::InvasionEnd::REFUSED,now_ms,result);
        return;
    }
    std::set<std::uint32_t> teammates;
    for (const auto& m:team->members()) teammates.insert(m.sign());
    if (invasion.sign<4 || invasion.sign>7 || teammates.contains(invasion.sign)) {
        EndInvasion(world.name,id,bbcoop::InvasionEnd::REFUSED,now_ms,result);
        return;
    }
    Member& invader=found->second;
    invader.visiting=world.name;
    invader.hostile=true;
    invasion.joined=true;
    invasion.joined_ms=now_ms;
    bbcoop::Envelope start;
    bbcoop::InvasionStart& message=*start.mutable_invasion_start();
    message.set_id(id);
    *message.mutable_session()=*world.session;
    message.mutable_session()->set_kind(invasion_rules.kind);
    message.mutable_session()->set_sign(invasion.sign);
    message.set_target(invasion.target);
    if (const auto place=world.places.find(invasion.target);place!=world.places.end())
        *message.mutable_at()=place->second.at.at();
    *message.mutable_owners()=world.owners.Message();
    bbcoop::Envelope joined;
    joined.mutable_invader_joined()->set_id(id);
    joined.mutable_invader_joined()->set_member(invasion.invader_name);
    joined.mutable_invader_joined()->set_target(invasion.target);
    joined.mutable_invader_joined()->set_name(invader.display);
    for (auto& [key,member]:members) {
        if (member.party==world.name && !member.hostile) {
            if (member.name==invasion.target) message.set_map(member.map);
            SendTo(member,joined,now_ms);
        }
    }
    // Existing hostiles are already in the world. Their *game* will
    // receive the same live vitals board and their native sockets can
    // exchange strict game channels only under the SAME visiting world.
    SendTo(invader,start,now_ms);
    result.log.append(QStringLiteral("invasions: %1 joins %2, id %3 sign %4")
        .arg(QString::fromStdString(invasion.invader_name),world.name)
        .arg(id).arg(invasion.sign));
}
''',"per-ID join and just-in-time cap")

    cpp=block(cpp,"void Service::EndInvasion(","void Service::CheckInvasion(",
        r'''void Service::EndInvasion(const QString& world, quint64 id,
    bbcoop::InvasionEnd::Reason reason, qint64 now_ms, Result& result) {
    const auto bucket=invasions.find(world);
    if (bucket==invasions.end()) return;
    const auto found=bucket->second.find(id);
    if (found==bucket->second.end()) return;
    const Invasion invasion=std::move(found->second);
    bucket->second.erase(found);
    if (bucket->second.empty()) invasions.erase(bucket);
    bbcoop::Envelope envelope;
    envelope.mutable_invasion_end()->set_id(id);
    envelope.mutable_invasion_end()->set_reason(reason);
    envelope.mutable_invasion_end()->set_invader(invasion.invader_name);
    if (const auto invader=members.find(invasion.invader);invader!=members.end()) {
        invader->second.visiting.clear();
        invader->second.hostile=false;
        SendTo(invader->second,envelope,now_ms);
    }
    for (auto& [key,member]:members)
        if (member.party==world && !member.hostile) SendTo(member,envelope,now_ms);
    cooldowns.Ended(world.toStdString(),invasion.invader_name,now_ms);
    result.log.append(QStringLiteral("invasions: id %1 of world %2 by %3 ended %4")
        .arg(id).arg(world,QString::fromStdString(invasion.invader_name),
                     QString::fromStdString(bbcoop::InvasionEnd::Reason_Name(reason))));
}

void Service::EndInvasion(const QString& world, bbcoop::InvasionEnd::Reason reason,
                          qint64 now_ms, Result& result) {
    const auto bucket=invasions.find(world);
    if (bucket==invasions.end()) return;
    std::vector<quint64> ids;
    for (const auto& [id,visitor]:bucket->second) ids.push_back(id);
    for (const quint64 id:ids) EndInvasion(world,id,reason,now_ms,result);
}
''',"per-ID vs whole-world end")

    cpp=block(cpp,"void Service::CheckInvasion(","QString Service::InvadedBy(",
        r'''void Service::CheckInvasion(const PartyWorld& world,const Member& member,
                              const bbcoop::Vitals& vitals,std::uint32_t wipe_before,
                              qint64 now_ms,Result& result) {
    const auto found=invasions.find(world.name);
    if (found==invasions.end()) return;
    if (vitals.boss()) {
        EndInvasion(world.name,bbcoop::InvasionEnd::BOSS,now_ms,result);
        return;
    }
    const bool active=std::ranges::any_of(found->second,[](const auto& item) {
        return item.second.joined;
    });
    if (!active) return;
    if (world.session && member.name==world.session->host() && vitals.vital()==3) {
        EndInvasion(world.name,bbcoop::InvasionEnd::TARGET_KILLED,now_ms,result);
        return;
    }
    const bbcoop::VitalsBoard board=world.boards.VitalsMessage();
    for (const auto& wipe:board.wipes())
        if (wipe.id()>wipe_before) {
            EndInvasion(world.name,bbcoop::InvasionEnd::PARTY_WIPED,now_ms,result);
            return;
        }
}
''',"boss/wipe/host ends all")

    cpp=block(cpp,"QString Service::InvadedBy(","void Service::InvasionLinkGone(",
        r'''QString Service::InvadedBy(quint64 link) const {
    for (const auto& [world,bucket]:invasions)
        for (const auto& [id,visitor]:bucket)
            if (visitor.invader==link) return world;
    return {};
}
''',"find invader in each world")

    cpp=one(cpp,
        "    if (const QString invaded = InvadedBy(link); !invaded.isEmpty()) {\n"
        "        EndInvasion(invaded, bbcoop::InvasionEnd::INVADER_LEFT, now_ms, result);\n"
        "    }",
        "    // "+TAG+": a disconnected hostile does NOT kick other hostiles.\n"
        "    if (const QString invaded=InvadedBy(link);!invaded.isEmpty()) {\n"
        "        const auto bucket=invasions.find(invaded);\n"
        "        if (bucket!=invasions.end()) {\n"
        "            for (const auto& [id,visitor]:bucket->second)\n"
        "                if (visitor.invader==link) {\n"
        "                    EndInvasion(invaded,id,bbcoop::InvasionEnd::INVADER_LEFT,now_ms,result);\n"
        "                    break;\n"
        "                }\n"
        "        }\n"
        "    }",
        "link loss ends single hostile")

    cpp=one(cpp,
        "        if (!invaded.isEmpty()) {\n"
        "            EndInvasion(invaded, bbcoop::InvasionEnd::INVADER_LEFT, now_ms, result);\n"
        "        }",
        "        if (!invaded.isEmpty()) {\n"
        "            const auto bucket=invasions.find(invaded);\n"
        "            if (bucket!=invasions.end()) {\n"
        "                for (const auto& [id,visitor]:bucket->second) {\n"
        "                    if (visitor.invader==member.key) {\n"
        "                        EndInvasion(invaded,id,bbcoop::InvasionEnd::INVADER_LEFT,now_ms,result);\n"
        "                        break;\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        }",
        "cancel request ends own hostile")

    # A fifth co-op player can arrive after ANY number of hostiles. Trim
    # only the excess visitors, most recently matched first, so remaining
    # valid hostiles are not unexpectedly torn down.
    before=r'''        if (const bbcoop::Team* team = lobby.TeamOf(member.lobby);
            team && team->members_size() >= static_cast<int>(InvasionMaxPlayers) &&
            !team->party().empty()) {
            const QString party =
                FolderOf(QByteArray::fromStdString(team->party()));
            if (invasions.contains(party)) {
                EndInvasion(party, bbcoop::InvasionEnd::REFUSED, now_ms, result);
            }
        }'''
    after=r'''        if (const bbcoop::Team* team=lobby.TeamOf(member.lobby);
            team && !team->party().empty()) {
            const QString party=FolderOf(QByteArray::fromStdString(team->party()));
            for (;;) {
                const auto bucket=invasions.find(party);
                if (bucket==invasions.end() ||
                    static_cast<size_t>(team->members_size())+bucket->second.size()
                        <= InvasionMaxPlayers) break;
                const quint64 newest=bucket->second.rbegin()->first;
                EndInvasion(party,newest,bbcoop::InvasionEnd::REFUSED,now_ms,result);
            }
        }'''
    cpp=one(cpp,before,after,"trim excess visitors when co-op grows")

    # Existing original C++ scenario expects a second invader to be
    # refused. Now the same started 2-person team has THREE hostile seats.
    test=one(test,
        '  // One invader a world: a second one is not matched, and is told so once\n'
        '  // its search runs out.\n',
        '  // '+TAG+': remaining real seats admit separate hosted invader IDs.\n',
        "update old one-invader world comment")
    test=one(test,
        '  CHECK(blue.notices.empty());\n'
        '  rig.Step(InvasionSearchMs);\n'
        '  CHECK(EndedFor(blue, bbcoop::InvasionEnd::NOT_FOUND));\n'
        '  CHECK(red.ends.empty());\n',
        '  CHECK(blue.notices.size() == 1);\n'
        '  rig.Step(InvasionNoticeMs);\n'
        '  CHECK(blue.invasion.has_value());\n'
        '  CHECK(blue.invasion->id()!=red.invasion->id());\n'
        '  CHECK(blue.invasion->session().sign()!=red.invasion->session().sign());\n'
        '  CHECK(rig.service.VisitingOf(blue.endpoint)==\n'
        '        rig.service.PartyOf(rig.a.endpoint));\n'
        '  CHECK(red.ends.empty());\n',
        "original Qt game-world multi visitor expectation")
    # Real 3 hostile case in ORIGINAL service with the 2 co-op players
    # from InvasionRig. Assert independent slots, arrival, cancellation,
    # route and selective cleanup, not just a capacity arithmetic test.
    test=one(test,
        "int AnInvasionNeedsTheServerAndTheTeamToAllowIt() {",
        r'''int ThreeInvadersShareTwoCooperatorsAndCleanupIndependently() {
  InvasionRig rig;
  Game blue{1003,"bl",14},green{1004,"gn",15},fourth{1005,"xx",16};
  for (Game* invader:std::vector<Game*>{&blue,&green,&fourth}) {
    rig.games.push_back(invader);
    invader->LobbyHello(true,rig.now);
  }
  rig.Step();
  for (Game* invader:std::vector<Game*>{&rig.red,&blue,&green}) {
    invader->Invade(60,rig.now);
    invader->Map(InvadedMap,rig.now);
    rig.Step();
    CHECK(invader->notices.size()==1);
  }
  CHECK(rig.a.notices.size()==3);
  fourth.Invade(60,rig.now);
  fourth.Map(InvadedMap,rig.now);
  rig.Step();
  CHECK(fourth.notices.empty()); // 2 co-op + 3 hostile = five TOTAL
  rig.Step(InvasionNoticeMs);
  for (Game* visitor:std::vector<Game*>{&rig.red,&blue,&green})
    CHECK(visitor->invasion.has_value());
  std::set<std::uint32_t> signs;
  for (Game* visitor:std::vector<Game*>{&rig.red,&blue,&green}) {
    signs.insert(visitor->invasion->session().sign());
    CHECK(rig.service.VisitingOf(visitor->endpoint)==
          rig.service.PartyOf(rig.a.endpoint));
  }
  CHECK(signs.size()==3);
  CHECK(signs.contains(4)&&signs.contains(5)&&signs.contains(6));
  CHECK(rig.Routes(rig.red,blue,0x06)); // same-world hostile-to-hostile
  CHECK(rig.Routes(blue,rig.red,0x14)); // native PvP hits, same map
  // One invader dies: unrelated two remain joined and can exchange
  // native GAME packets with the co-op team.
  blue.Vitals(InvadedMap,3,rig.now,60);
  rig.Step();
  CHECK(EndedFor(blue,bbcoop::InvasionEnd::INVADER_DIED));
  CHECK(rig.service.VisitingOf(blue.endpoint).isEmpty());
  CHECK(rig.service.VisitingOf(rig.red.endpoint)==
        rig.service.PartyOf(rig.a.endpoint));
  CHECK(rig.service.VisitingOf(green.endpoint)==
        rig.service.PartyOf(rig.a.endpoint));
  CHECK(rig.Routes(rig.red,rig.a,0x06));
  CHECK(!rig.Routes(blue,rig.a,0x06));
  rig.Allow(false); // host turns invasions off, ALL hostiles exit
  CHECK(EndedFor(rig.red,bbcoop::InvasionEnd::INVADERS_OFF));
  CHECK(EndedFor(green,bbcoop::InvasionEnd::INVADERS_OFF));
  CHECK(rig.service.VisitingOf(rig.red.endpoint).isEmpty());
  CHECK(rig.service.VisitingOf(green.endpoint).isEmpty());
  return 0;
}

int AnInvasionNeedsTheServerAndTheTeamToAllowIt() {''',
        "three real visitors functional test")
    test=one(test,
        '      {"AnInvaderJoinsATeamWorldAfterANotice",\n'
        '       AnInvaderJoinsATeamWorldAfterANotice},',
        '      {"AnInvaderJoinsATeamWorldAfterANotice",\n'
        '       AnInvaderJoinsATeamWorldAfterANotice},\n'
        '      {"ThreeInvadersShareTwoCooperatorsAndCleanupIndependently",\n'
        '       ThreeInvadersShareTwoCooperatorsAndCleanupIndependently},',
        "register original Qt test")
    return dict(zip(FILES,(h,cpp,policy,rules,link,test)))

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    src={}
    for p in FILES:
        f=root/p
        if not f.is_file() or f.is_symlink():
            raise ValueError(f"{TAG}: missing or symlink source: {p}")
        src[p]=f.read_text("utf-8")
    changes=patch(src)
    for p,t in changes.items():
        (root/p).write_text(t,encoding="utf-8")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_multi_invader_server_v108.py DISPOSABLE_YT_SOURCE")
    stage(Path(sys.argv[1]))
    print("SHYT_V108_ORIGINAL_QT_MULTINVADER_SERVER_3_TOTAL_FIVE_STAGED")
