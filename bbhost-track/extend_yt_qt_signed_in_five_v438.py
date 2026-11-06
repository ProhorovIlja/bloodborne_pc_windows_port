#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V438 adds original hosted sign-in identity binding to five encrypted YT links.

Original YT v1.4.0 Qt Hub::SetSignIn runs on the decrypted Noise-NK
Hello and server credentials, before creating a linked online ID.
This synthetic fixture does not verify a real player's platform login
or produce P2P authority; it proves server callbacks are honored.
"""
from __future__ import annotations
import argparse
from pathlib import Path

START='''  Net net;
  const Endpoint Maria{0x7F000001u, 40004u};'''
AFTER='''  Net net;
  // Separate synthetic server-side credentials per OnlineID: an
  // attacker cannot claim any existing member merely by changing
  // GameFrame.sender or resending a signed-in-looking Hello.
  const std::map<QByteArray,QByteArray> identities={
      {"Kaniel","unique-k"},{"Ada","unique-a"},{"Eileen","unique-e"},
      {"Maria","unique-m"},{"Gehrman","unique-g"}};
  std::size_t checked_signins=0;
  net->SetSignIn([&](const QByteArray& id,const QByteArray& secret,bool) {
    ++checked_signins;
    const auto it=identities.find(id);
    return SignInVerdict{
      it!=identities.end() && it->second==secret,{}};
  });
  const Endpoint Maria{0x7F000001u, 40004u};'''
JOIN='''    auto linked=net.Receive(
        people[i].first,HelloFrom(people[i].second),static_cast<qint64>(i));'''
JOIN_NEW='''    auto linked=net.Receive(
        people[i].first,
        HelloFrom(people[i].second,Build,
                  identities.at(QByteArray(people[i].second))),
        static_cast<qint64>(i));'''
PROOF='''  CHECK(net->Members()==5 && net.unopened==0);'''
PROOF_NEW='''  CHECK(net->Members()==5 && net.unopened==0 &&
        checked_signins==people.size());

  // The original server's hosted sign-in must refuse another endpoint
  // pretending to be Ada with a wrong credential. Neither the roster
  // nor Ada's authenticated virtual endpoint may change.
  const Endpoint impostor{0x7F000001u, 40155u};
  const auto forged=net.Receive(
      impostor,HelloFrom("Ada",Build,"not-Ada-secret"),9);
  const auto refusal=SentTo(forged,impostor);
  CHECK(refusal.size()==1);
  const auto verdict=DecodeWelcome(refusal[0]);
  CHECK(verdict && !verdict->accepted);
  CHECK(net->Members()==5 && !net->VirtualOf(impostor) &&
        net->VirtualOf(Ada)==VirtualEndpointOf("Ada") &&
        checked_signins==people.size()+1u);'''
REBIND='''  const auto linked=net.Receive(ada_moved,HelloFrom("Ada"),70);'''
REBIND_NEW='''  const auto linked=net.Receive(
      ada_moved,HelloFrom("Ada",Build,identities.at("Ada")),70);'''
TAIL='''  CHECK(net.unopened==0);
  std::cout<<"V437 YT ORIGINAL NOISE-NK FIVE HUNTER ROUTE REBIND PASS\\n";'''
TAIL_NEW='''  CHECK(net.unopened==0 && checked_signins==people.size()+2u);
  std::cout<<"V437 YT ORIGINAL NOISE-NK FIVE HUNTER ROUTE REBIND PASS\\n";
  std::cout<<"V438 YT ORIGINAL FIVE DISTINCT HOSTED SIGN-IN IDENTITIES PASS\\n";'''

def extend(path:Path)->None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>260000:
        raise ValueError("original server test overlay unavailable/oversized")
    s=path.read_text(encoding="utf-8")
    for before in (START,JOIN,PROOF,REBIND,TAIL):
        if s.count(before)!=1:
            raise ValueError("V437 original source test drift")
    updated=s
    for before,after in (
        (START,AFTER),(JOIN,JOIN_NEW),(PROOF,PROOF_NEW),
        (REBIND,REBIND_NEW),(TAIL,TAIL_NEW)):
        updated=updated.replace(before,after)
    if updated.count("V438 YT ORIGINAL FIVE DISTINCT HOSTED SIGN-IN IDENTITIES PASS")!=1:
        raise ValueError("V438 credential marker missing")
    path.write_text(updated,encoding="utf-8")
    print("SHYT_V438_HOSTED_FIVE_SIGNED_IN_YT_CREDENTIAL_QT_TEST_ADDED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--overlay-test",type=Path,required=True)
    args=p.parse_args()
    try:extend(args.overlay_test)
    except (ValueError,OSError,UnicodeError) as e:
        raise SystemExit("SHYT_V438_SIGN_IN_QT_FIXTURE_REFUSED: "+
                         type(e).__name__) from None
