#!/usr/bin/env python3
"""V67: native Qt shadNet Hub ephemeral, revocable pair snapshots.

Derived from V66, not the raw upstream. A snapshot is NOT a bearer token,
MAC, session secret or outbound grant. Client input must NEVER be accepted
as a valid snapshot. Future secure encrypted rendezvous may consume only
server-owned snapshots after revalidating at issuance time.
"""
from __future__ import annotations
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
V66=HERE/"patch_authenticated_pair.py"
HEADER="server/src/server_link.h"
SOURCE="server/src/server_link.cpp"
TEST="server/tests/test_server_link.cpp"

def one(s: str, old: str, new: str, label: str) -> str:
    n=s.count(old)
    if n!=1: raise ValueError(f"V67 {label}: expected one anchor, got {n}")
    return s.replace(old,new,1)

def transform(files: dict[str,str]) -> dict[str,str]:
    if set(files)!={HEADER,SOURCE,TEST}:
        raise ValueError("V67 requires complete V66 Qt Hub trio")
    h, cpp, test=(files[x] for x in (HEADER,SOURCE,TEST))
    if "CaptureDirectPairSnapshot" in h or "CaptureDirectPairSnapshot" in cpp or "CaptureDirectPairSnapshot" in test:
        raise ValueError("V67 already applied")
    h=one(h,
'''    int Members() const {
''',
'''    // V67: server-only ephemeral pair snapshot. NOT a cryptographic grant
    // and NEVER acceptable from a client or untrusted datagram.
    struct DirectPairSnapshot {
        Endpoint source;
        Endpoint destination;
        quint64 source_generation = 0;
        quint64 destination_generation = 0;
        QByteArray source_account;
        QByteArray destination_account;
        QByteArray build;
        QString party;
        quint64 world_epoch = 0;
        qint64 issued_at_ms = 0;
        qint64 expires_at_ms = 0;
    };
    // Must be provided by the authoritative game-world state, with nonzero
    // revision when the party/map/team/ownership/rule scope changes.
    using DirectWorldEpoch = std::function<quint64(const Endpoint&, const Endpoint&)>;
    void SetDirectWorldEpoch(DirectWorldEpoch epoch) {
        direct_world_epoch = std::move(epoch);
    }
    std::optional<DirectPairSnapshot> CaptureDirectPairSnapshot(
        const Endpoint& source, const Endpoint& destination,
        qint64 now_ms, qint64 requested_lifetime_ms) const;
    bool ValidateDirectPairSnapshot(const DirectPairSnapshot& snapshot,
                                    qint64 now_ms) const;

    int Members() const {
''',"public pair snapshot")
    h=one(h,
'''        qint64 last_heard_ms = 0;
''',
'''        qint64 last_heard_ms = 0;
        quint64 hello_generation = 0; // each successful Hello changes session identity
''',"link generation")
    h=one(h,
'''    DirectConsent direct_consent; // unconfigured in production => no P2P grant
''',
'''    DirectConsent direct_consent; // unconfigured in production => no P2P grant
    DirectWorldEpoch direct_world_epoch; // unconfigured => no snapshot
    quint64 next_hello_generation = 1; // 0 is exhausted: permanently fail closed
''',"server-owned epoch provider and counter")

    cpp=one(cpp,
'''#include <algorithm>
''',
'''#include <algorithm>
#include <limits>
''',"limits header")
    cpp=one(cpp,
'''        !SameTeam(source, destination))
''',
'''        !SameTeam(source, destination) || next_hello_generation == 0 ||
        a.hello_generation == 0 || b.hello_generation == 0)
''',"V66 pair gate includes unforgeable local incarnation")
    cpp=one(cpp,
'''Hub::Result Hub::Receive(const Endpoint& from, const QByteArray& datagram, qint64 now_ms) {
''',
'''// V67: 5-second maximum server-INTERNAL candidate snapshot; never send
// or treat as a cryptographic authorization token. Revalidate only at
// candidate issuing/renewal, NOT once per gameplay packet (CPU budget).
std::optional<Hub::DirectPairSnapshot> Hub::CaptureDirectPairSnapshot(
    const Endpoint& source, const Endpoint& destination,
    qint64 now_ms, qint64 lifetime_ms) const {
    constexpr qint64 MaxLifetimeMs = 5000;
    if (lifetime_ms <= 0 || lifetime_ms > MaxLifetimeMs ||
        now_ms < 0 || now_ms > std::numeric_limits<qint64>::max() - lifetime_ms ||
        !direct_world_epoch || !DirectPairEligible(source, destination, now_ms))
        return std::nullopt;
    const auto a = members.constFind(source.Key());
    const auto b = members.constFind(destination.Key());
    if (a == members.cend() || b == members.cend())
        return std::nullopt;
    const QString party = party_of(source);
    const quint64 epoch = direct_world_epoch(source, destination);
    if (party.isEmpty() || party != party_of(destination) || epoch == 0)
        return std::nullopt;
    // Every value is based on authoritative in-process records, not
    // a client-supplied "server_verified" boolean.
    return DirectPairSnapshot{source,destination,
        a->hello_generation,b->hello_generation,
        a->online_id,b->online_id,a->build,party,epoch,
        now_ms,now_ms+lifetime_ms};
}

bool Hub::ValidateDirectPairSnapshot(const DirectPairSnapshot& grant,
                                     qint64 now_ms) const {
    if (now_ms < 0 || grant.issued_at_ms < 0 ||
        grant.expires_at_ms <= grant.issued_at_ms ||
        grant.expires_at_ms-grant.issued_at_ms > 5000 ||
        now_ms < grant.issued_at_ms || now_ms >= grant.expires_at_ms ||
        !direct_world_epoch ||
        !DirectPairEligible(grant.source,grant.destination,now_ms))
        return false;
    const auto a=members.constFind(grant.source.Key());
    const auto b=members.constFind(grant.destination.Key());
    if (a == members.cend() || b == members.cend() ||
        a->hello_generation != grant.source_generation ||
        b->hello_generation != grant.destination_generation ||
        a->online_id != grant.source_account ||
        b->online_id != grant.destination_account ||
        a->build != grant.build || b->build != grant.build ||
        party_of(grant.source) != grant.party ||
        party_of(grant.destination) != grant.party ||
        direct_world_epoch(grant.source,grant.destination) != grant.world_epoch)
        return false;
    return true;
}

Hub::Result Hub::Receive(const Endpoint& from, const QByteArray& datagram, qint64 now_ms) {
''',"candidate snapshot implementation")
    cpp=one(cpp,
'''    link.build = hello->build;
    link.last_heard_ms = now_ms;
''',
'''    link.build = hello->build;
    // Successful re-hello (even same socket/account/build) invalidates
    // every prior snapshot: no stale P2P pair survives a new sign-in.
    link.hello_generation = next_hello_generation;
    if (next_hello_generation != 0) {
        if (next_hello_generation == std::numeric_limits<quint64>::max())
            next_hello_generation = 0; // exhausted, deny forever
        else
            ++next_hello_generation;
    }
    link.last_heard_ms = now_ms;
''',"re-hello generation")

    test=one(test,
'''int HelloAndBuilds() {
''',
'''int DirectPairSnapshotRevocation() {
  Hub hub;
  hub.SetSignIn([](const QByteArray& who,const QByteArray& password) {
    return !who.isEmpty() && password == "test-only-password";
  });
  QString shared_party = "room-1";
  const Endpoint rebound{0x7F000001,40008};
  hub.SetPartyOf([&](const Endpoint& from) -> QString {
    return from == Kaniel || from == Ada || from == rebound
           ? shared_party : QString{};
  });
  bool consent=true;
  hub.SetDirectConsent([&](const QByteArray&,const QByteArray&) { return consent; });
  quint64 epoch = 42;
  hub.Receive(Kaniel,HelloFrom("Kaniel",Build,"test-only-password"),0);
  hub.Receive(Ada,HelloFrom("Ada",Build,"test-only-password"),0);
  CHECK(!hub.CaptureDirectPairSnapshot(Kaniel,Ada,1,1000));
  hub.SetDirectWorldEpoch([&](const Endpoint&, const Endpoint&) { return epoch; });
  CHECK(!hub.CaptureDirectPairSnapshot(Kaniel,Ada,1,0));
  CHECK(!hub.CaptureDirectPairSnapshot(Kaniel,Ada,1,5001));
  CHECK(!hub.CaptureDirectPairSnapshot(Kaniel,Ada,-1,100));
  auto snap=hub.CaptureDirectPairSnapshot(Kaniel,Ada,1,5000);
  CHECK(snap.has_value());
  CHECK(snap->world_epoch==42 && snap->party=="room-1");
  CHECK(hub.ValidateDirectPairSnapshot(*snap,1));
  CHECK(hub.ValidateDirectPairSnapshot(*snap,2)); // both peers still fresh
  CHECK(!hub.ValidateDirectPairSnapshot(*snap,5001));
  auto tampered=*snap;
  tampered.source_generation++;
  CHECK(!hub.ValidateDirectPairSnapshot(tampered,1));
  tampered=*snap;
  tampered.destination_generation++;
  CHECK(!hub.ValidateDirectPairSnapshot(tampered,1));
  tampered=*snap;
  tampered.build="another client";
  CHECK(!hub.ValidateDirectPairSnapshot(tampered,1));
  tampered=*snap;
  tampered.expires_at_ms+=5001;
  CHECK(!hub.ValidateDirectPairSnapshot(tampered,1));
  consent=false;
  CHECK(!hub.ValidateDirectPairSnapshot(*snap,2));
  consent=true;
  epoch++;
  CHECK(!hub.ValidateDirectPairSnapshot(*snap,2));
  auto newepoch=hub.CaptureDirectPairSnapshot(Kaniel,Ada,2,5000);
  CHECK(newepoch && hub.ValidateDirectPairSnapshot(*newepoch,2));
  shared_party="room-2";
  CHECK(!hub.ValidateDirectPairSnapshot(*newepoch,2));
  auto newparty=hub.CaptureDirectPairSnapshot(Kaniel,Ada,2,5000);
  CHECK(newparty && hub.ValidateDirectPairSnapshot(*newparty,2));
  // SAME socket/account/build repeated Hello must invalidate prior snapshot.
  hub.Receive(Ada,HelloFrom("Ada",Build,"test-only-password"),3);
  CHECK(!hub.ValidateDirectPairSnapshot(*newparty,3));
  auto newhello=hub.CaptureDirectPairSnapshot(Kaniel,Ada,3,5000);
  CHECK(newhello && hub.ValidateDirectPairSnapshot(*newhello,3));
  // Rebinding Ada to another real endpoint removes the former identity.
  hub.Receive(rebound,HelloFrom("Ada",Build,"test-only-password"),4);
  CHECK(!hub.ValidateDirectPairSnapshot(*newhello,4));
  CHECK(!hub.CaptureDirectPairSnapshot(Kaniel,Ada,4,1000));
  auto rebounded=hub.CaptureDirectPairSnapshot(Kaniel,rebound,4,1000);
  CHECK(rebounded && hub.ValidateDirectPairSnapshot(*rebounded,4));
  // 3s inactivity ends a direct lease even if its requested TTL is longer.
  CHECK(!hub.ValidateDirectPairSnapshot(*rebounded,3005));
  epoch=0;
  CHECK(!hub.CaptureDirectPairSnapshot(Kaniel,rebound,5,1000));
  std::cout << "direct pair snapshot revocation: ok\\n";
  return 0;
}

int HelloAndBuilds() {
''',"real server snapshot tests")
    test=one(test,
'''DirectPairAdmission() != 0 ||''',
'''DirectPairAdmission() != 0 || DirectPairSnapshotRevocation() != 0 ||''',"native server test main")
    return {HEADER:h,SOURCE:cpp,TEST:test}

def apply_to_checkout(root: Path)->None:
    old={p:(root/p).read_text("utf-8") for p in (HEADER,SOURCE,TEST)}
    new=transform(old)
    for p,s in new.items(): (root/p).write_text(s,"utf-8")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("pinned_checkout",type=Path)
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location("sh_v66",V66)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.apply_to_checkout(a.pinned_checkout)
    apply_to_checkout(a.pinned_checkout)
    print("SHYT_V67_QT_PAIR_EPOCH_SNAPSHOT_PATCH_PASS")
