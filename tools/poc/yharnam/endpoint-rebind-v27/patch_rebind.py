#!/usr/bin/env python3
"""V27 fail-closed patch for stale virtual endpoint after same-socket account change."""
from pathlib import Path
LINK="server/src/server_link.cpp"
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
        result.log.append(QStringLiteral("server link: account switch at %1: retired %2")
                              .arg(from.Text(), QString::fromUtf8(prior.online_id)));
    }
    const bool again = members.contains(from.Key());
    Link& link = members[from.Key()];''',
          'identity-rebind cleanup')
    return s
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.source.resolve()==a.output.resolve():p.error('in-place mutation refused')
    a.output.write_text(transform(a.source.read_text('utf-8')),encoding='utf-8')
