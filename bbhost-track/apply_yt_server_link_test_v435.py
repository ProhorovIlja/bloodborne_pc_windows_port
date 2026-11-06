#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Overlay original YT 1.4.0 Qt server_link integration test, unchanged upstream.

The source-pinned original invasion test sent a frame from Ada with
frame.sender='Red'; V434 must reject that. Preserve the genuine invader
route test with Ada's own sender and add a separate spoof/refusal check.
No Qt source files in the original checkout are modified or deployed.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

SOURCE_BLOB="e0a52246a48a287c7c7798d54fa1da6aff552b5e"
INVADER_OLD='''  result = hub.Receive(
      Ada, Encode(Data{VirtualEndpointOf("Red"), GamePacketsFrame(frame)}), 20);
  CHECK(SentTo(result, Red).size() == 1);'''
INVADER_NEW='''  // V435: original source test used the visiting Red's sender field
  // in Ada's outbound frame, which is a spoof. New Hub must refuse it.
  result = hub.Receive(
      Ada, Encode(Data{VirtualEndpointOf("Red"), GamePacketsFrame(frame)}), 20);
  CHECK(result.sends.isEmpty());
  auto ada_frame = frame;
  ada_frame.sender = "Ada";
  result = hub.Receive(
      Ada, Encode(Data{VirtualEndpointOf("Red"), GamePacketsFrame(ada_frame)}), 21);
  CHECK(SentTo(result, Red).size() == 1);'''
ANCHOR='''} // namespace

int main() {'''
ADD=R'''
// V435: real original Hub link->game sender trust boundary, not just
// standalone GameFrame codec. Net::Receive goes through the original
// YT datagram encoder, session Hub and real pair/route policy.
int V435AuthenticatedGameSender() {
  using BloodborneCoop::PacketClass;
  Net hub;
  hub->SetPacketRoutes(
      [](const Endpoint &, const Endpoint &, u32) { return true; });
  hub.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  hub.Receive(Ada, HelloFrom("Ada"), 0);
  BloodborneCoop::GameFrame frame{"Kaniel", 7, 9, 1, {}};
  frame.entries.push_back({PacketClass::Unreliable, 12, PacketOn(0x06)});
  const auto forward = [&](const BloodborneCoop::GameFrame& f, qint64 when) {
    return hub.Receive(
        Kaniel, Encode(Data{VirtualEndpointOf("Ada"), GamePacketsFrame(f)}),
        when);
  };
  auto result = forward(frame, 10);
  CHECK(SentTo(result, Ada).size() == 1);
  const auto authentic = DecodeData(SentTo(result, Ada)[0]);
  CHECK(authentic && authentic->peer == VirtualEndpointOf("Kaniel"));
  frame.sender = "Ada";
  CHECK(forward(frame, 11).sends.isEmpty()); // spoof another signed-in link
  frame.sender = "eileen";
  CHECK(forward(frame, 12).sends.isEmpty()); // unknown signed-in link
  frame.sender = "Kaniel";
  frame.instance = 0;
  CHECK(forward(frame, 13).sends.isEmpty()); // game has no session
  frame.instance = 6;
  CHECK(forward(frame, 14).sends.isEmpty()); // game uses odd random run
  frame.instance = 7;
  frame.entries[0].packet[4] = char(0xff);
  CHECK(forward(frame, 15).sends.isEmpty()); // invalid nested payload length
  frame.entries[0].packet = PacketOn(0x06);
  CHECK(SentTo(forward(frame, 16), Ada).size() == 1);
  frame.entries.clear(); // original GameLink ACK-only is still legal
  CHECK(SentTo(forward(frame, 17), Ada).size() == 1);

  // Missing RoutePolicy is not license to pass an unvalidated frame.
  Net no_policy;
  no_policy.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  no_policy.Receive(Ada, HelloFrom("Ada"), 0);
  const auto game = Encode(Data{
    VirtualEndpointOf("Ada"), GamePacketsFrame(frame)});
  CHECK(no_policy.Receive(Kaniel, game, 20).sends.isEmpty());
  const auto control = Encode(Data{
    VirtualEndpointOf("Ada"),
    QByteArray::fromHex("ffffffff") + "SHAD" + char(0x41) + "vitals"});
  CHECK(SentTo(no_policy.Receive(Kaniel, control, 21), Ada).size() == 1);
  std::cout << "V435 YT original Qt Hub sender spoofing/no-route: ok\n";
  return 0;
}
'''
MAIN='''       AnInvaderSharesTheVisitedTeamsRelay() != 0) {'''
MAIN_NEW='''       AnInvaderSharesTheVisitedTeamsRelay() != 0 ||
       V435AuthenticatedGameSender() != 0) {'''
def patch(yt:Path,out:Path)->None:
    if not yt.is_dir() or yt.is_symlink() or out.is_symlink():
        raise ValueError("bad source/test output location")
    obj=subprocess.check_output([
        "git","-C",str(yt),"rev-parse",
        "HEAD:server/tests/test_server_link.cpp"],
        text=True,timeout=10).strip()
    if obj!=SOURCE_BLOB:
        raise ValueError("original YT 1.4.0 Qt Hub test source drift")
    original=yt/"server/tests/test_server_link.cpp"
    if original.is_symlink() or original.stat().st_size>180000:
        raise ValueError("original Qt Hub test unavailable or oversized")
    s=original.read_text(encoding="utf-8")
    for before in (INVADER_OLD,ANCHOR,MAIN):
        if s.count(before)!=1:raise ValueError("ambiguous original test anchor")
    fixed=(s.replace(INVADER_OLD,INVADER_NEW)
             .replace(ANCHOR,ADD+'\n'+ANCHOR)
             .replace(MAIN,MAIN_NEW))
    if out.exists():
        raise ValueError("refuse overwrite of existing Qt integration test")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(fixed,encoding="utf-8")
    assert original.read_text(encoding="utf-8")==s
    print("SHYT_V435_ORIGINAL_QT_HUB_INTEGRATION_TEST_OVERLAY_PASS")
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--yt",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    try:patch(args.yt,args.out)
    except (ValueError,OSError,UnicodeError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        raise SystemExit("SHYT_V435_QT_HUB_INTEGRATION_OVERLAY_REFUSED: "+
                         type(exc).__name__) from None
