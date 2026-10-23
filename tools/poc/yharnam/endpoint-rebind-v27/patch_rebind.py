#!/usr/bin/env python3
"""V27 fail-closed patch for stale virtual endpoint after same-socket account change."""
from pathlib import Path
LINK="server/src/server_link.cpp"
LINK_H="server/src/server_link.h"
LINK_SERVER="server/src/link_server.cpp"
TEST="server/tests/test_server_link.cpp"
HEADER="server/src/sh_endpoint_rebind.hpp"
HERE=Path(__file__).resolve().parent
def one(s,old,new,name):
    n=s.count(old)
    if n!=1:raise ValueError(f'V27 {name}: pinned source drift, found {n} anchors')
    return s.replace(old,new,1)
def transform(s):
    if "SH-ENDPOINT-REBIND-V27" in s:raise ValueError("V27 already applied")
    s=one(s,'#include "server_link.h"',
          '#include "server_link.h"\n#include "sh_endpoint_rebind.hpp" // SH-ENDPOINT-REBIND-V27',
          'include')
    s=one(s,
          '''    const bool again = members.contains(from.Key());
    Link& link = members[from.Key()];''',
          '''    // An already-linked endpoint changing account must discard its prior
    // virtual address, game packet routes and old co-op world membership.
    // Ordinary repeated Hello for the SAME account remains uninterrupted.
    if (const auto old_it = members.find(from.Key()); old_it != members.end() &&
        SeamlessHunt::LinkRebind::MustRetire(
            true, old_it->online_id, hello->online_id)) {
        const Link prior = *old_it;
        // Tell co-op peers while the party->endpoint mapping still refers to
        // the old player, not the new claimed identity.
        TellOthers(prior, MemberState::Gone, 0, result);
        Unlink(from.Key()); // also erases by_virtual + in-flight pair routes
        result.gone.append(prior.endpoint); // clears the old co-op world
        result.retired_online_ids.append(prior.online_id); // clear matchmaking too
        result.log.append(QStringLiteral("server link: account switch at %1: retired %2")
                              .arg(from.Text(), QString::fromUtf8(prior.online_id)));
    }
    const bool again = members.contains(from.Key());
    Link& link = members[from.Key()];''',
          'identity-rebind cleanup')
    return s

def transform_header(s):
    if "SH-ENDPOINT-REBIND-V27" in s:raise ValueError("V27 already applied to Hub header")
    return one(s,
        '''        QList<Endpoint> gone; // links forgotten''',
        '''        QList<Endpoint> gone; // links forgotten
        // SH-ENDPOINT-REBIND-V27: old ID on same socket after switching accounts.
        QList<QByteArray> retired_online_ids;''',
        'Hub::Result retired account identities')

def transform_server(s):
    if "SH-ENDPOINT-REBIND-V27" in s:raise ValueError("V27 already applied to link server")
    return one(s,
        '''    // Phase 7: a linked game's address for the rooms and signaling is its virtual one, known from
    // its hello.
    for (const auto& linked : result.linked) {''',
        '''    // SH-ENDPOINT-REBIND-V27: remove old matchmaking virtual endpoints
    // BEFORE registering new IDs. Ordinary same-account reconnects are untouched.
    for (const QByteArray& retired : result.retired_online_ids) {
        QWriteLocker lk(&m_shared->matching.udpLock);
        m_shared->matching.udpExt.remove(QString::fromUtf8(retired));
    }
    // Phase 7: a linked game's address for the rooms and signaling is its virtual one, known from
    // its hello.
    for (const auto& linked : result.linked) {''',
        'matchmaking address cleanup')

def transform_test(s):
    if "SH-ENDPOINT-REBIND-V27" in s:raise ValueError("V27 already applied to Qt tests")
    s=one(s,'''int Relays() {''',
'''// SH-ENDPOINT-REBIND-V27: a same-address account change must unlink its
// previous virtual endpoint and notify the old team before admitting new ID.
int ChangedAccountOnSameEndpoint() {
  Hub hub;
  auto result = hub.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  CHECK(DecodeWelcome(SentTo(result, Kaniel).value(0))->accepted);
  result = hub.Receive(Ada, HelloFrom("Ada"), 10);
  CHECK(DecodeWelcome(SentTo(result, Ada).value(0))->accepted);
  result = hub.Receive(Kaniel, HelloFrom("Eileen"), 20);
  CHECK(DecodeWelcome(SentTo(result, Kaniel).value(0))->accepted);
  CHECK(result.gone.size() == 1 && result.gone[0] == Kaniel);
  CHECK(result.retired_online_ids.size() == 1 &&
        result.retired_online_ids[0] == "Kaniel");
  CHECK(hub.Members() == 2 && hub.VirtualOf(Kaniel) == VirtualEndpointOf("Eileen"));
  // In the old source the stale by_virtual entry would reach Eileen here.
  result = hub.Receive(Ada, Encode(Data{VirtualEndpointOf("Kaniel"), GameFrame}), 30);
  CHECK(SentTo(result, Kaniel).isEmpty());
  result = hub.Receive(Ada, Encode(Data{VirtualEndpointOf("Eileen"), GameFrame}), 40);
  CHECK(SentTo(result, Kaniel).size() == 1);
  result = hub.Receive(Kaniel, HelloFrom("Eileen"), 50);
  CHECK(result.gone.isEmpty() && result.retired_online_ids.isEmpty());
  std::cout << "server link changed account: virtual routes retired\n";
  return 0;
}

int Relays() {''',
        'Qt identity-switch test')
    s=one(s,
        '''  if (Contracts() != 0 || HelloAndBuilds() != 0 || Relays() != 0 ||''',
        '''  if (Contracts() != 0 || HelloAndBuilds() != 0 ||
      ChangedAccountOnSameEndpoint() != 0 || Relays() != 0 ||''',
        'Qt test runner')
    return s

def transform_all(sources):
    return {LINK: transform(sources[LINK]),
            LINK_H: transform_header(sources[LINK_H]),
            LINK_SERVER: transform_server(sources[LINK_SERVER]),
            TEST: transform_test(sources[TEST]),
            HEADER: (HERE/'sh_endpoint_rebind.hpp').read_text('utf8')}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.source.resolve()==a.output.resolve():p.error('in-place mutation refused')
    a.output.write_text(transform(a.source.read_text('utf-8')),encoding='utf-8')
