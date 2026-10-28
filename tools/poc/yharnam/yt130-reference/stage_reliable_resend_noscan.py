#!/usr/bin/env python3
"""Eliminate O(entries × retransmits) scan while preserving quiet-recovery.

The original post-quiet Flush forces all unacked entries (including just-fresh)
to be resend-due. So NO-SCAN was incorrect: a fresh reliable could be emitted
twice in one flush. Index just the fresh reliable sequence IDs; older unacked
map keys are already unique. No changes to backoff, wire, authentication.
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
OLD_SCAN = """            if (now_ms - out.sent_ms >= out.wait_ms &&
                std::ranges::none_of(entries, [&](const GameFrameEntry& entry) {
                    return entry.packet_class == PacketClass::Reliable && entry.seq == seq;
                })) {"""
NEW_SCAN = """            // Quiet-peer recovery can make even freshly emitted entries
            // immediately due. Never duplicate those in the same frame.
            // Older unacked entries have distinct map keys; only check the
            // reliable sequences freshly sent in this particular Flush.
            if (now_ms - out.sent_ms >= out.wait_ms &&
                !fresh_reliable.contains(seq)) {"""
OLD_INCLUDE = "#include <span>\n#include <string>"
NEW_INCLUDE = "#include <span>\n#include <string>\n#include <unordered_set>"
OLD_FRESH = """        std::vector<GameFrameEntry> entries;
        for (Outgoing& out : fresh) {
            entries.push_back({out.packet_class, out.seq, out.packet});
            if (out.packet_class == PacketClass::Reliable) {"""
NEW_FRESH = """        std::vector<GameFrameEntry> entries;
        std::unordered_set<u32> fresh_reliable;
        fresh_reliable.reserve(fresh.size());
        for (Outgoing& out : fresh) {
            entries.push_back({out.packet_class, out.seq, out.packet});
            if (out.packet_class == PacketClass::Reliable) {
                fresh_reliable.insert(out.seq);"""
FRESH_INVARIANT = """                out.sent_ms = now_ms;
                out.wait_ms = settings.resend_ms;
                unacked.emplace(out.seq, std::move(out));"""

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
CPP_TEST += """// A peer returning from silence makes even NEW unacked entries due immediately.
// The fresh set must suppress a second copy of that new sequence in this Flush.
int GameLinkQuietPeerResumeKeepsNewPacketUnique() {
  GameLinkPeer sender{"sender", 71};
  const std::vector<u8> old_packet{1};
  const std::vector<u8> new_packet{2};
  sender.Send(PacketClass::Reliable, old_packet, 0);
  CHECK(sender.Flush(0).size() == 1);
  // A peer was heard, then went silent long enough for quiet_ms.
  GameFrame ping{"receiver", 72, 0, 0, {}};
  sender.Receive(ping, 100);
  CHECK(!sender.Flush(10200).empty());
  sender.Receive(ping, 10210); // Sets heard_since_quiet.
  sender.Send(PacketClass::Reliable, new_packet, 10211);
  const auto resumed = sender.Flush(10211);
  std::set<u32> sequences;
  size_t packets = 0;
  for (const auto &frame : resumed) {
    for (const auto &entry : frame.entries) {
      CHECK(entry.packet_class == PacketClass::Reliable);
      CHECK(sequences.insert(entry.seq).second);
      ++packets;
    }
  }
  CHECK(packets == 2);  // new #1 plus retry of old #0
  CHECK(sequences.count(0) == 1 && sequences.count(1) == 1);
  CHECK(sender.Resends() == 1); // never count fresh #1 as a resend
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
      {"GameLinkQuietPeerResumeKeepsNewPacketUnique",
       GameLinkQuietPeerResumeKeepsNewPacketUnique},
"""

def once(source, old, new, area):
    if source.count(old) != 1:
        raise ValueError("Exact official source drift: " + area)
    return source.replace(old, new)

def rewrite(header, test):
    if "No linear scan of all just-emitted frames" in header or "GameLinkBurstResendSequenceDedupAndAck" in test:
        raise ValueError("Already staged")
    if header.count(FRESH_INVARIANT) != 1:
        raise ValueError("Fresh reliable resend timing invariant changed")
    if "settings.resend_ms = 200;" not in test and "NonHostedTeamEditsAreCoalescedAndStartStillWorks" not in test:
        raise ValueError("Original native functional world test stage is required")
    if "s64 resend_ms = 150;" not in header or "size_t max_resends = 64;" not in header:
        raise ValueError("Original no-storm reliability limits changed")
    header = once(header, OLD_INCLUDE, NEW_INCLUDE, "unordered sequence include")
    header = once(header, OLD_FRESH, NEW_FRESH, "only fresh seq index")
    return once(header, OLD_SCAN, NEW_SCAN, "GameLinkPeer::Flush"), once(test, OLD_TEST, NEW_TEST, "real C++ test main")

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Pinned original YT1.3 checkout required")
    files = [root / HEADER, root / TEST]
    for name, file in zip((HEADER, TEST), files):
        if git(root, "rev-parse", "HEAD:" + name) != BLOBS[name] or file.is_symlink():
            raise ValueError("Original blob drift or symlink: " + name)
    if git(root, "diff", "--", HEADER):
        raise ValueError("Original GameLinkPeer must not already be patched")
    if not git(root, "diff", "--", TEST):
        raise ValueError("Original C++ world test stager did not run")
    out = rewrite(*(f.read_text(encoding="utf-8") for f in files))
    for file, source in zip(files, out):
        file.write_text(source, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_RELIABLE_RETRANSMIT_REDUNDANT_LINEAR_SCAN_REMOVED")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_original_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_original_yt130_checkout)
