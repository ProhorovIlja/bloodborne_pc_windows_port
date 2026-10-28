#!/usr/bin/env python3
"""Source-pinned O(log N) reliable resend de-duplication in native YT1.3 GameLinkPeer.

Preserves the same frame order, ACK, resend timing, backoff, anti-storm caps,
quiet-peer behavior and wire encoding. Requires the original test fixture staged.
"""
from pathlib import Path
import argparse
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
HEADER = "server/coop/game_link.h"
TEST = "server/tests/test_bloodborne_world.cpp"
BLOBS = {
    HEADER: "5029581251bfe5decf562c19a10bdd079150cdad",
    TEST: "2ec55d02101545723e9889bebe83d8b1d531a1c7",
}

OLD_INCLUDE = "#include <span>\n#include <string>"
NEW_INCLUDE = "#include <span>\n#include <set>\n#include <string>"

OLD_ENTRY = """        std::vector<GameFrameEntry> entries;
        for (Outgoing& out : fresh) {
            entries.push_back({out.packet_class, out.seq, out.packet});
            if (out.packet_class == PacketClass::Reliable) {"""
NEW_ENTRY = """        std::vector<GameFrameEntry> entries;
        // Reuse a sequence index rather than scanning an ever-growing entry
        // vector for every retransmit. Frame ordering and payloads do not change.
        std::set<u32> emitted_reliable;
        for (Outgoing& out : fresh) {
            entries.push_back({out.packet_class, out.seq, out.packet});
            if (out.packet_class == PacketClass::Reliable) {
                emitted_reliable.insert(out.seq);"""

OLD_LOOKUP = """            if (now_ms - out.sent_ms >= out.wait_ms &&
                std::ranges::none_of(entries, [&](const GameFrameEntry& entry) {
                    return entry.packet_class == PacketClass::Reliable && entry.seq == seq;
                })) {"""
NEW_LOOKUP = """            if (now_ms - out.sent_ms >= out.wait_ms &&
                !emitted_reliable.contains(seq)) {"""

OLD_RESEND = """                ++resends;
                ++resent;
                entries.push_back({out.packet_class, out.seq, out.packet});
            }
        }"""
NEW_RESEND = """                ++resends;
                ++resent;
                entries.push_back({out.packet_class, out.seq, out.packet});
                emitted_reliable.insert(seq);
            }
        }"""

CPP_TEST = """// An ACK/retransmit storm should not queue the same reliable seq twice
// in one Flush, even if 320 messages are due at once. Preserve wire order.
int GameLinkBurstResendSequenceDedupAndAck() {
  GameLinkPeer sender{"load-sender", 71};
  GameLinkPeer receiver{"load-receiver", 72};
  for (u32 i = 0; i < 320; ++i) {
    const std::vector<u8> payload{static_cast<u8>(i % 251)};
    sender.Send(PacketClass::Reliable, payload, 100);
  }
  const auto original = sender.Flush(100);
  std::set<u32> sent;
  for (const auto &frame : original) {
    for (const auto &entry : frame.entries) {
      CHECK(entry.packet_class == PacketClass::Reliable);
      CHECK(sent.insert(entry.seq).second);
    }
  }
  CHECK(sent.size() == 320);
  CHECK(sender.Unacked() == 320);
  CHECK(sender.Flush(101).empty());
  const auto retried = sender.Flush(400);
  std::set<u32> retry_seq;
  for (const auto &frame : retried) {
    for (const auto &entry : frame.entries) {
      CHECK(entry.packet_class == PacketClass::Reliable);
      CHECK(retry_seq.insert(entry.seq).second);
    }
  }
  CHECK(retry_seq.size() == 64); // The unchanged max_resends flood guard.
  CHECK(sender.Resends() == 64);
  size_t delivered = 0;
  for (const auto &frame : original) {
    delivered += receiver.Receive(frame, 401).size();
  }
  CHECK(delivered == 320);
  const auto acknowledgement = receiver.Flush(402);
  CHECK(!acknowledgement.empty());
  for (const auto &frame : acknowledgement) {
    sender.Receive(frame, 403);
  }
  CHECK(sender.Unacked() == 0);
  CHECK(sender.Flush(600).empty()); // No stale resends after the ACK.
  return 0;
}

"""
OLD_TEST = """int main() {
  const std::vector<std::pair<const char *, std::function<int()>>> tests{
"""
NEW_TEST = CPP_TEST + """int main() {
  const std::vector<std::pair<const char *, std::function<int()>>> tests{
      {"GameLinkBurstResendSequenceDedupAndAck",
       GameLinkBurstResendSequenceDedupAndAck},
"""

def once(s, old, new, where):
    if s.count(old) != 1:
        raise ValueError("Pinned original source drift at " + where)
    return s.replace(old, new)

def rewrite(header, test):
    if "emitted_reliable" in header or "GameLinkBurstResendSequenceDedupAndAck" in test:
        raise ValueError("Source already optimized")
    if "NonHostedTeamEditsAreCoalescedAndStartStillWorks" not in test:
        raise ValueError("Original native world test stage not applied")
    header = once(header, OLD_INCLUDE, NEW_INCLUDE, "include")
    header = once(header, OLD_ENTRY, NEW_ENTRY, "fresh send index")
    header = once(header, OLD_LOOKUP, NEW_LOOKUP, "retransmit duplicate guard")
    header = once(header, OLD_RESEND, NEW_RESEND, "resent index")
    test = once(test, OLD_TEST, NEW_TEST, "real world C++ test")
    return header, test

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Only the exact original YT1.3 checkout is allowed")
    files = [root / HEADER, root / TEST]
    for name, path in zip((HEADER, TEST), files):
        if git(root, "rev-parse", "HEAD:" + name) != BLOBS[name]:
            raise ValueError("Source blob SHA changed: " + name)
        if path.is_symlink():
            raise ValueError("Refuse symlink source: " + name)
    if git(root, "diff", "--", HEADER):
        raise ValueError("Original GameLinkPeer header already modified")
    if not git(root, "diff", "--", TEST):
        raise ValueError("Official C++ world stage missing")
    changed = rewrite(*(p.read_text(encoding="utf-8") for p in files))
    for path, source in zip(files, changed):
        path.write_text(source, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_RELIABLE_RESEND_SEQUENCE_INDEXED_NATIVE_CPP_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_original_yt130_checkout", type=Path)
    apply(parser.parse_args().disposable_original_yt130_checkout)
