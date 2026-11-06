#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Augment V435's isolated original YT Qt Hub test with genuine Noise-NK game relay.

Only a synthetic two-client localhost test, not game-ready P2P or live
NetSync. Never changes the pinned checkout or production Fornex.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ANCHOR="} // namespace\n\nint main() {"
MAIN="       V435AuthenticatedGameSender() != 0) {"
ADDED=R'''
// V436: original Noise-NK/SHLK4 encrypted sender -> authoritative Hub
// -> original GameFrame router -> encrypted second client's SHLK link.
// This exercises the REAL source-pinned YT relay, not a mock protocol.
int V436OriginalEncryptedGameRelay() {
  using BloodborneCoop::PacketClass;
  Net net;
  net->SetPacketRoutes([](const Endpoint &from, const Endpoint &to, u32 ch) {
    return from != to && ch != 0x31;
  });
  auto first = net.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  CHECK(DecodeWelcome(SentTo(first, Kaniel).value(0))->accepted);
  auto second = net.Receive(Ada, HelloFrom("Ada"), 1);
  CHECK(DecodeWelcome(SentTo(second, Ada).value(0))->accepted);
  CHECK(net->Members() == 2 && net.unopened == 0);

  BloodborneCoop::GameFrame msg{"Kaniel", 7, 0, 0, {}};
  msg.entries={
    {PacketClass::Reliable, 17, PacketOn(0x31)}, // forbidden by room route
    {PacketClass::Unreliable, 2, PacketOn(0x31)}, // forbidden; no seq
    {PacketClass::Unreliable, 3, PacketOn(0x06)}  // allowed movement
  };
  auto send = [&](const BloodborneCoop::GameFrame &game, qint64 ms) {
    return net.Receive(Kaniel, Encode(Data{
      VirtualEndpointOf("Ada"), GamePacketsFrame(game)}), ms);
  };
  auto result=send(msg,10);
  CHECK(SentTo(result,Ada).size()==1 && net.unopened==0);
  const auto forwarded=DecodeData(SentTo(result,Ada)[0]);
  CHECK(forwarded && forwarded->peer==VirtualEndpointOf("Kaniel"));
  CHECK(forwarded->frame.size()>9 &&
        static_cast<quint8>(forwarded->frame[8])==
            BloodborneCoop::GamePacketsType);
  auto parsed=BloodborneCoop::DecodeGameFrame({
    reinterpret_cast<const u8*>(forwarded->frame.constData())+9,
    static_cast<size_t>(forwarded->frame.size()-9)});
  CHECK(parsed && parsed->sender=="Kaniel" &&
        parsed->instance==7 && parsed->entries.size()==2);
  CHECK(parsed->entries[0].packet_class==PacketClass::Reliable &&
        parsed->entries[0].seq==17 &&
        parsed->entries[0].packet==BloodborneCoop::DroppedNativePacket());
  CHECK(parsed->entries[1].packet_class==PacketClass::Unreliable &&
        parsed->entries[1].packet==PacketOn(0x06));

  // Same encrypted link, false GameFrame sender: Hub must not forward,
  // even if the room's packet-route callback would allow ch 0x06.
  msg.sender="Ada";
  CHECK(send(msg,11).sends.isEmpty());
  msg.sender="Eileen";
  CHECK(send(msg,12).sends.isEmpty());
  msg.sender="Kaniel";
  msg.instance=0;  // missing current game run
  CHECK(send(msg,13).sends.isEmpty());
  msg.instance=7;
  msg.entries={{PacketClass::Unreliable,3,PacketOn(0x06)}};
  CHECK(SentTo(send(msg,14),Ada).size()==1 && net.unopened==0);

  // Replay exactly the same original encrypted SHLK datagram (not a
  // freshly re-sealed new message). Source link's Noise counter must
  // discard replay before GameFrame reaches any recipient.
  QByteArray sealed=Encode(Data{
    VirtualEndpointOf("Ada"),GamePacketsFrame(msg)});
  auto trailer=net.games.at(Kaniel.Key()).Seal(MutableSpan(sealed));
  CHECK(trailer.has_value());
  sealed+=Bytes(*trailer);
  auto once=net.hub.Receive(Kaniel,sealed,15);
  CHECK(SentTo(once,Ada).size()==1);
  const auto replay_count=net->Replays();
  const auto twice=net.hub.Receive(Kaniel,sealed,16);
  CHECK(twice.sends.isEmpty() && net->Replays()==replay_count+1);

  // Keep the authoritative original Hub context, reject game data
  // when the room/map/owner route callback has not been installed.
  Net no_policy;
  no_policy.Receive(Kaniel,HelloFrom("Kaniel"),0);
  no_policy.Receive(Ada,HelloFrom("Ada"),0);
  CHECK(no_policy.Receive(Kaniel,Encode(Data{
      VirtualEndpointOf("Ada"),GamePacketsFrame(msg)}),20).sends.isEmpty());
  std::cout<<"V436 YT ORIGINAL NOISE-NK 2-PEER AUTHENTIC GAME RELAY PASS\n";
  return 0;
}
'''
def extend(p:Path)->None:
    if p.is_symlink() or not p.is_file() or p.stat().st_size>200000:
        raise ValueError("missing/oversized V435 test-only Qt overlay")
    s=p.read_text(encoding="utf-8")
    if s.count(ANCHOR)!=1 or s.count(MAIN)!=1 or s.count("V435AuthenticatedGameSender()")!=1:
        raise ValueError("V435 original Qt test anchor drift")
    updated=s.replace(ANCHOR,ADDED+"\n"+ANCHOR).replace(
        MAIN,"       V435AuthenticatedGameSender() != 0 ||\n"
             "       V436OriginalEncryptedGameRelay() != 0) {")
    if updated.count("V436OriginalEncryptedGameRelay()")!=2:
        raise ValueError("unexpected real encrypted relay test injection")
    p.write_text(updated,encoding="utf-8")
    print("SHYT_V436_ORIGINAL_ENCRYPTED_QT_GAMELINK_2_PEER_FIXTURE_ADDED")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--overlay-test",required=True,type=Path)
    a=parser.parse_args()
    try: extend(a.overlay_test)
    except (ValueError,OSError,UnicodeError) as e:
        raise SystemExit("SHYT_V436_ORIGINAL_QT_GAME_RELAY_FIXTURE_REFUSED: "+
                         type(e).__name__) from None
