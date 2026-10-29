#!/usr/bin/env python3
"""V72 actual pinned server world membership/epoch authority binding.

This source-only overlay patches the REAL Qt shadNet world and LinkServer,
building atop V67 Hub::SetDirectWorldEpoch. Requires full pinned candidate,
and makes NO P2P grants or secret/address disclosures. Mutual consent is
still unconfigured in real server, so actual direct eligibility stays DENY.
"""
from __future__ import annotations

WORLD_H="server/src/bloodborne_world.h"
WORLD_CPP="server/src/bloodborne_world.cpp"
LINK_CPP="server/src/link_server.cpp"
REVISION_H="server/src/sh_world_revision.hpp"
WORLD_TEST="server/tests/test_bloodborne_world.cpp"

def one(s: str, before: str, after: str, label: str)->str:
    n=s.count(before)
    if n!=1:
        raise ValueError(f"V72 {label}: pinned source mismatch ({n})")
    return s.replace(before,after,1)

def transform(files: dict[str,str])->dict[str,str]:
    if set(files)!={WORLD_H,WORLD_CPP,LINK_CPP}:
        raise ValueError("V72 expected actual world H/CPP + LinkServer CPP")
    h,cpp,link=(files[p] for p in (WORLD_H,WORLD_CPP,LINK_CPP))
    if "DirectWorldEpoch" in h or "SetDirectWorldEpoch" in link:
        raise ValueError("V72 double patch")
    h=one(h,
'''    bool RoutesPacket(const ServerLink::Endpoint& from, const ServerLink::Endpoint& to,
                      std::uint32_t channel) const;
''',
'''    bool RoutesPacket(const ServerLink::Endpoint& from, const ServerLink::Endpoint& to,
                      std::uint32_t channel) const;
    // V72: server-owned revocable group/map/area version for the existing V67
    // internal candidate snapshot. Called ONLY while evaluating grants, not
    // per relayed or direct game datagram. Zero denies candidate issuance.
    quint64 DirectWorldEpoch(const ServerLink::Endpoint& from,
                            const ServerLink::Endpoint& to) const;
''',"world public epoch accessor")
    cpp=one(cpp,
'''#include "bloodborne_world.h"
''',
'''#include "bloodborne_world.h"
#include "sh_world_revision.hpp"
''',"shared server revision helper")
    cpp=one(cpp,
'''bool Service::RoutesPacket(const ServerLink::Endpoint& from, const ServerLink::Endpoint& to,
''',
'''quint64 Service::DirectWorldEpoch(const ServerLink::Endpoint& from,
                                  const ServerLink::Endpoint& to) const {
    if(from == to) return 0;
    const auto a=members.find(from.Key());
    const auto b=members.find(to.Key());
    if(a==members.end() || b==members.end()) return 0;
    const Member& first=a->second;
    const Member& second=b->second;
    // The server, not client, owns and updates team/cut/map/owner metadata.
    if(first.party.isEmpty() || first.party!=second.party ||
       first.map==0 || first.map!=second.map ||
       (!first.cut_from.isEmpty() && first.cut_from==second.party) ||
       (!second.cut_from.isEmpty() && second.cut_from==first.party))
        return 0;
    const auto world=worlds.find(first.party);
    if(world==worlds.end()) return 0;
    const PartyWorld& party=world->second;
    const auto reset=party.map_reset_ms.find(first.map);
    const std::uint64_t reset_revision=reset==party.map_reset_ms.end() ? 0 :
        static_cast<std::uint64_t>(reset->second);
    const std::string owner=party.owners.OwnerOf(first.map);
    const SeamlessHunt::Hybrid::WorldRevisionInput input{
        party.host.Epoch(),reset_revision,party.session_run,
        first.map,second.map,owner,true,true,false,false
    };
    return SeamlessHunt::Hybrid::BoundWorldRevision(input);
}

bool Service::RoutesPacket(const ServerLink::Endpoint& from, const ServerLink::Endpoint& to,
''',"live server world revision implementation")
    link=one(link,
'''    m_link.SetPartyOf([this](const ServerLink::Endpoint& link) { return m_world.PartyOf(link); });
''',
'''    m_link.SetPartyOf([this](const ServerLink::Endpoint& link) { return m_world.PartyOf(link); });
    // V72: the same world that guards actual shadNet combat/area routing now
    // supplies the V67 internal grant's version. Direct consent is NOT yet
    // configured: server-only revision lookup enables no new transport.
    m_link.SetDirectWorldEpoch([this](const ServerLink::Endpoint& a,
                                      const ServerLink::Endpoint& b) {
        return m_world.DirectWorldEpoch(a,b);
    });
''',"Qt LinkServer wires real game-world version")
    return {WORLD_H:h,WORLD_CPP:cpp,LINK_CPP:link}

def transform_test(test: str)->str:
    if "SHYT_V72_WORLD_AUTHORITY_TEST" in test:
        raise ValueError("V72 test already applied")
    test=one(test,
'''  // No map said yet: what the game does on its own.
  CHECK(routes(host, guest, 0x06) && routes(host, guest, 0x04));
''',
'''  // SHYT_V72_WORLD_AUTHORITY_TEST: no active map = no P2P snapshot.
  CHECK(service.DirectWorldEpoch(host.endpoint,guest.endpoint)==0);
  // No map said yet: what the game does on its own.
  CHECK(routes(host, guest, 0x06) && routes(host, guest, 0x04));
''',"real world test before map")
    test=one(test,
'''  CHECK(routes(host, guest, 0x06) && routes(guest, host, 0x06));
  CHECK(!routes(host, guest2, 0x06) && !routes(guest2, guest, 0x31));
''',
'''  CHECK(routes(host, guest, 0x06) && routes(guest, host, 0x06));
  const quint64 current_epoch=service.DirectWorldEpoch(host.endpoint,guest.endpoint);
  CHECK(current_epoch!=0);
  CHECK(service.DirectWorldEpoch(guest.endpoint,host.endpoint)==current_epoch);
  CHECK(service.DirectWorldEpoch(host.endpoint,guest2.endpoint)==0);
  CHECK(service.DirectWorldEpoch(host.endpoint,host.endpoint)==0);
  CHECK(!routes(host, guest2, 0x06) && !routes(guest2, guest, 0x31));
''',"real map owner world test")
    test=one(test,
'''  CHECK(!service.RoutesPacket(stranger, host.endpoint, 0x06));
  CHECK(service.RoutesPacket(stranger, host.endpoint, 0x10));
''',
'''  CHECK(!service.RoutesPacket(stranger, host.endpoint, 0x06));
  CHECK(service.RoutesPacket(stranger, host.endpoint, 0x10));
  CHECK(service.DirectWorldEpoch(stranger,host.endpoint)==0);
''',"unknown socket never P2P granted")
    test=one(test,
'''  CHECK(service.PartyOf(b.endpoint).isEmpty());
  CHECK(a.map_board.members_size() == 1 &&
''',
'''  CHECK(service.PartyOf(b.endpoint).isEmpty());
  CHECK(service.DirectWorldEpoch(a.endpoint,b.endpoint)==0);
  CHECK(a.map_board.members_size() == 1 &&
''',"removed team invalidates grant")
    return test
