#!/usr/bin/env python3
"""V76 coherent Qt game world P2P snapshot, no live grant or network listeners.

Apply AFTER V74: server uses account-bound active links, both opt-ins and
same world to produce one authoritative snapshot for future authenticated
TLS grant issuer. This is NOT a public HTTP/SHLK endpoint.
"""
from __future__ import annotations

WORLD_H="server/src/bloodborne_world.h"
WORLD_CPP="server/src/bloodborne_world.cpp"
WORLD_TEST="server/tests/test_bloodborne_world.cpp"

def exactly(source,old,new,label):
    n=source.count(old)
    if n!=1: raise ValueError(f"V76 {label}: expected one source anchor, found {n}")
    return source.replace(old,new,1)

def patch(files):
    if set(files)!={WORLD_H,WORLD_CPP,WORLD_TEST}:
        raise ValueError("V76 requires exact composed Qt world implementation and original tests")
    h,cpp,test=(files[p] for p in (WORLD_H,WORLD_CPP,WORLD_TEST))
    if "CaptureDirectPairScope" in h or "CaptureDirectPairScope" in cpp:
        raise ValueError("V76 repeated patch")
    h=exactly(h,
'''    bool PairDirectConsent(const QByteArray& a,const QByteArray& b) const;
''',
'''    // Internal world-authoritative read-only rendezvous scope. Do NOT send
    // its real endpoints over plaintext SHLK/HTTP. Only a future mutually
    // authenticated TLS client/account binding may request encrypted offers.
    struct DirectPairScope {
        QByteArray first_account;
        QByteArray second_account;
        ServerLink::Endpoint first_physical{};
        ServerLink::Endpoint second_physical{};
        ServerLink::Endpoint first_virtual{};
        ServerLink::Endpoint second_virtual{};
        quint64 world_revision=0;
    };
    std::optional<DirectPairScope> CaptureDirectPairScope(
        const QByteArray& a,const QByteArray& b) const;
    bool PairDirectConsent(const QByteArray& a,const QByteArray& b) const;
''',"add snapshot API only")
    start=cpp.index("bool Service::PairDirectConsent(")
    finish=cpp.index("\nquint64 Service::DirectWorldEpoch(",start)
    old=cpp[start:finish]
    if "const Member* left=nullptr" not in old or "return DirectWorldEpoch(left_endpoint,right_endpoint)!=0;" not in old:
        raise ValueError("V76 source unexpected consent implementation")
    replacement='''std::optional<Service::DirectPairScope> Service::CaptureDirectPairScope(
    const QByteArray& a,const QByteArray& b) const {
    if(a.isEmpty() || b.isEmpty() || a==b) return std::nullopt;
    const Member* left=nullptr;
    const Member* right=nullptr;
    ServerLink::Endpoint left_endpoint{},right_endpoint{};
    // O(player_count) ONLY during a secure grant request, NEVER per packet.
    // This must not trust a claimed name, NAT candidate, or P2P probe.
    for(const auto& [key,member]:members) {
        if(member.online_id!=a && member.online_id!=b) continue;
        const auto found=endpoints.find(key);
        if(found==endpoints.end()) return std::nullopt;
        if(member.online_id==a) {
            if(left) return std::nullopt;  // account attached twice
            left=&member;left_endpoint=found->second;
        } else {
            if(right) return std::nullopt;
            right=&member;right_endpoint=found->second;
        }
    }
    if(!left || !right || !left->direct_p2p_opt_in ||
       !right->direct_p2p_opt_in ||
       left->party.isEmpty() || left->party!=right->party ||
       left_endpoint==right_endpoint ||
       !left_endpoint.ipv4 || !left_endpoint.port ||
       !right_endpoint.ipv4 || !right_endpoint.port)
        return std::nullopt;
    const quint64 revision=DirectWorldEpoch(left_endpoint,right_endpoint);
    if(!revision) return std::nullopt;
    const auto first_virtual=ServerLink::VirtualEndpointOf(a);
    const auto second_virtual=ServerLink::VirtualEndpointOf(b);
    if(!first_virtual.ipv4 || !first_virtual.port ||
       !second_virtual.ipv4 || !second_virtual.port ||
       first_virtual==second_virtual)
        return std::nullopt;
    return DirectPairScope{a,b,left_endpoint,right_endpoint,
                           first_virtual,second_virtual,revision};
}

bool Service::PairDirectConsent(const QByteArray& a,const QByteArray& b) const {
    return CaptureDirectPairScope(a,b).has_value();
}
'''
    cpp=cpp[:start]+replacement+cpp[finish:]
    test=exactly(test,
'''  CHECK(service.PairDirectConsent("host","guest"));
  CHECK(service.PairDirectConsent("guest","host"));
''',
'''  CHECK(service.PairDirectConsent("host","guest"));
  CHECK(service.PairDirectConsent("guest","host"));
  // V76: stable account-bound, world-scoped current real+virtual endpoints.
  const auto captured=service.CaptureDirectPairScope("host","guest");
  CHECK(captured.has_value());
  CHECK(captured->first_account=="host");
  CHECK(captured->second_account=="guest");
  CHECK(captured->first_physical==a.endpoint);
  CHECK(captured->second_physical==b.endpoint);
  CHECK(captured->first_virtual==ServerLink::VirtualEndpointOf("host"));
  CHECK(captured->second_virtual==ServerLink::VirtualEndpointOf("guest"));
  CHECK(captured->world_revision==
        service.DirectWorldEpoch(a.endpoint,b.endpoint));
  CHECK(!service.CaptureDirectPairScope("host","stranger"));
  CHECK(!service.CaptureDirectPairScope("host","host"));
''',"scope matches live real Qt member state")
    test=exactly(test,
'''  CHECK(!service.PairDirectConsent("host","guest"));
  a.Map(Yharnam,now+30);
''',
'''  CHECK(!service.PairDirectConsent("host","guest"));
  CHECK(!service.CaptureDirectPairScope("host","guest"));
  a.Map(Yharnam,now+30);
''',"loading invalidates snapshot")
    test=exactly(test,
'''  CHECK(!service.PairDirectConsent("host","guest"));
  b.Hello(now+50,Party,true);
''',
'''  CHECK(!service.PairDirectConsent("host","guest"));
  CHECK(!service.CaptureDirectPairScope("host","guest"));
  b.Hello(now+50,Party,true);
''',"opt-out invalidates snapshot")
    test=exactly(test,
'''  service.Forget(b.endpoint);
  CHECK(!service.PairDirectConsent("host","guest"));
''',
'''  service.Forget(b.endpoint);
  CHECK(!service.PairDirectConsent("host","guest"));
  CHECK(!service.CaptureDirectPairScope("host","guest"));
''',"disconnect invalidates snapshot")
    return {WORLD_H:h,WORLD_CPP:cpp,WORLD_TEST:test}
