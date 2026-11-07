#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V440: bounded NAT-rebind churn regression on original YT v1.4.0 Qt Hub.

Extends only V438's temporary CI test overlay. A valid already-authenticated
member repeatedly moves physical UDP endpoints; the real original Qt Hub must
retain exactly five members, retire the previous endpoint and route encrypted
game frames only from the currently authenticated endpoint.

Not direct P2P, an endpoint/room grant, BBHost gameplay NetSync, or a latency
benchmark. Does not modify upstream checkout, game data, or live Fornex.
"""
from __future__ import annotations
import argparse
from pathlib import Path

BEFORE = '''  CHECK(net.unopened==0 && checked_signins==people.size()+2u);
  std::cout<<"V437 YT ORIGINAL NOISE-NK FIVE HUNTER ROUTE REBIND PASS\\n";'''
AFTER = r'''  CHECK(net.unopened==0 && checked_signins==people.size()+2u);

  // V440: churn the SAME legitimate hunter through 24 new UDP sources.
  // Every new original Noise-NK Hello must be hosted-sign-in checked, the
  // previous source must lose its virtual YT endpoint, and the other four
  // players must remain connected. This is real Hub logic, NOT P2P.
  Endpoint active_ada=ada_moved;
  for(std::uint16_t i=0;i<24u;++i) {
    const Endpoint next{0x7F000001u,static_cast<std::uint16_t>(40200u+i)};
    const qint64 at=100+3*static_cast<qint64>(i);
    const auto migrated=net.Receive(
        next,HelloFrom("Ada",Build,identities.at("Ada")),at);
    CHECK(SentTo(migrated,next).size()==1);
    const auto response=DecodeWelcome(SentTo(migrated,next)[0]);
    CHECK(response && response->accepted);
    CHECK(migrated.gone.size()==1 && migrated.gone[0]==active_ada);
    CHECK(net->Members()==5 && net.unopened==0);
    CHECK(net->VirtualOf(next)==VirtualEndpointOf("Ada") &&
          !net->VirtualOf(active_ada));
    CHECK(net->VirtualOf(Kaniel)==VirtualEndpointOf("Kaniel") &&
          net->VirtualOf(Eileen)==VirtualEndpointOf("Eileen") &&
          net->VirtualOf(Maria)==VirtualEndpointOf("Maria") &&
          net->VirtualOf(Gehrman)==VirtualEndpointOf("Gehrman"));
    team[next.Key()]=team.at(active_ada.Key());
    maps[next.Key()]=maps.at(active_ada.Key());
    team.erase(active_ada.Key());
    maps.erase(active_ada.Key());
    // Never accept a packet from the OLD UDP endpoint after the move.
    CHECK(transmit(active_ada,"Ada","Kaniel",0x06u,at+1).sends.isEmpty());
    CHECK(SentTo(transmit(next,"Ada","Kaniel",0x06u,at+2),
                 Kaniel).size()==1);
    active_ada=next;
  }
  CHECK(net->Members()==5 && net.unopened==0 &&
        checked_signins==people.size()+2u+24u);
  std::cout<<"V440 YT ORIGINAL FIVE MEMBER AUTHENTIC REBIND CHURN PASS\n";
  std::cout<<"V437 YT ORIGINAL NOISE-NK FIVE HUNTER ROUTE REBIND PASS\n";'''

def extend(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 280000:
        raise ValueError("missing or oversized V438 Qt overlay")
    original = path.read_text(encoding="utf-8")
    if original.count(BEFORE) != 1:
        raise ValueError("V438 source anchor drift: refusal to guess")
    updated = original.replace(BEFORE, AFTER, 1)
    if updated.count("V440 YT ORIGINAL FIVE MEMBER AUTHENTIC REBIND CHURN PASS") != 1:
        raise ValueError("V440 test marker not unique")
    path.write_text(updated, encoding="utf-8")
    print("SHYT_V440_ORIGINAL_FIVE_MEMBER_QT_REBIND_CHURN_ADDED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay-test", type=Path, required=True)
    args = parser.parse_args()
    try:
        extend(args.overlay_test)
    except (ValueError, OSError, UnicodeError) as exc:
        raise SystemExit("SHYT_V440_QT_CHURN_OVERLAY_REFUSED: " +
                         type(exc).__name__) from None
