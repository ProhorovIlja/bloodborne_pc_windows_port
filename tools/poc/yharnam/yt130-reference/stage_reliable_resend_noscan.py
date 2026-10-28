#!/usr/bin/env python3
"""Drop provably redundant O(entries × retransmits) duplicate scan in YT1.3.

The original fresh-to-unacked transition sets sent_ms=now and a strictly
positive resend delay before traversing unacked. Therefore freshly emitted
reliable sequences cannot also be due for resend in the SAME flush; all old
unacked entries are map-key unique. Keep existing exact wire and backoff.
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
NEW_SCAN = """            // fresh reliable entries were inserted into unacked with
            // sent_ms=now_ms and positive resend_ms, so they cannot be due
            // during this same Flush. Older unacked entries have unique seq
            // map keys. No linear scan of all just-emitted frames is needed.
            if (now_ms - out.sent_ms >= out.wait_ms) {"""
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
OLD_TEST = """int main() {
  const std::vector<std::pair<const char *, std::function<int()>>> tests{
"""
NEW_TEST = CPP_TEST + """int main() {
  const std::vector<std::pair<const char *, std::function<int()>>> tests{
      {"GameLinkBurstResendSequenceDedupAndAck",
       GameLinkBurstResendSequenceDedupAndAck},
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
