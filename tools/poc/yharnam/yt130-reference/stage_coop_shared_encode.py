#!/usr/bin/env python3
"""Share encoding of identical reliable Coop(7) broadcasts in pinned YT1.3 C++.

No wire, authority, ACK, order or recipient changes. A single protobuf payload
is encoded once per board or entries broadcast, then copied into each existing
member's reliable CoopStream, preserving per-peer independent resend/ACK.
"""
from pathlib import Path
import argparse
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP = "server/src/bloodborne_world.cpp"
HEADER = "server/src/bloodborne_world.h"
TEST = "server/tests/test_bloodborne_world.cpp"
BLOBS = {
    CPP: "eca8c30d6fb78099b0f64a52388fd7d65f926e19",
    HEADER: "dfdbd49a30427b71c95e520dbc77498b521bce93",
    TEST: "2ec55d02101545723e9889bebe83d8b1d531a1c7",
}

SEND_BEFORE = """void Service::SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms) {
    // Diagnostic: one count per original reliable *message*, before chunking.
    ++m_diagEnvelopes[static_cast<int>(envelope.body_case())];
    member.stream.Send(EncodeEnvelope(envelope), now_ms);
    if (!member.to_flush) {
        member.to_flush = true;
        flush_now.push_back(&member);
    }
}"""

SEND_AFTER = """void Service::SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms) {
    SendEncoded(member, EncodeEnvelope(envelope), static_cast<int>(envelope.body_case()), now_ms);
}

void Service::SendEncoded(Member& member, const std::vector<u8>& bytes,
                          int body_case, qint64 now_ms) {
    // The same original message count for EVERY recipient; stream.Send still
    // copies bytes into each member's independent reliable ACK/resend stream.
    ++m_diagEnvelopes[body_case];
    member.stream.Send(bytes, now_ms);
    if (!member.to_flush) {
        member.to_flush = true;
        flush_now.push_back(&member);
    }
}"""

ENTRY_BEFORE = """    for (auto& [key, member] : members) {
        if (member.party == world.name) {
            SendTo(member, envelope, now_ms);
        }
    }
    world.heartbeat_ms = now_ms;
}"""
ENTRY_AFTER = """    // All recipients of this world-log entry see identical protobuf bytes.
    // Lazy encoding avoids work when the party has no linked members.
    std::optional<std::vector<u8>> encoded;
    for (auto& [key, member] : members) {
        if (member.party == world.name) {
            if (!encoded) {
                encoded = EncodeEnvelope(envelope);
            }
            SendEncoded(member, *encoded, static_cast<int>(envelope.body_case()), now_ms);
        }
    }
    world.heartbeat_ms = now_ms;
}"""

BOARD_BEFORE = """    for (const bbcoop::Envelope& board : boards) {
        if (only != nullptr) {
            SendTo(*only, board, now_ms);
            continue;
        }
        for (auto& [key, member] : members) {
            if (member.party == world.name) {
                SendTo(member, board, now_ms);
            }
        }
    }
}"""
BOARD_AFTER = """    for (const bbcoop::Envelope& board : boards) {
        if (only != nullptr) {
            // The single-recipient initial snapshot stays byte-identical.
            SendTo(*only, board, now_ms);
            continue;
        }
        // Each board is identical for recipients in this same party, including
        // the joined invader line that VitalsBoardOf already constructed.
        std::optional<std::vector<u8>> encoded;
        for (auto& [key, member] : members) {
            if (member.party == world.name) {
                if (!encoded) {
                    encoded = EncodeEnvelope(board);
                }
                SendEncoded(member, *encoded, static_cast<int>(board.body_case()), now_ms);
            }
        }
    }
}"""

H_BEFORE = """    void SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms);"""
H_AFTER = """    void SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms);
    // Identical wire payload; every member retains its own reliable stream.
    void SendEncoded(Member& member, const std::vector<u8>& encoded,
                     int body_case, qint64 now_ms);"""

CPP_TEST = r"""int IdenticalCoopBroadcastsKeepPartyWorldAndReliableDelivery() {
  Service service{{}};
  Game host{1000, "host", 11};
  Game guest{1001, "guest", 12};
  Game outsider{1002, "outsider", 13};
  const std::vector<Game *> players{&host, &guest, &outsider};
  qint64 now = 1'000'000;
  host.Hello(now);
  guest.Hello(now);
  outsider.Hello(now, "other:isolated");
  Pump(service, players, now);
  CHECK(host.welcome && host.welcome->accepted());
  CHECK(guest.welcome && guest.welcome->accepted());
  CHECK(outsider.welcome && outsider.welcome->accepted());
  CHECK(service.Parties() == 2);
  const u32 map = 0x18000000;
  host.Map(map, now + 100);
  guest.Map(map, now + 100);
  outsider.Map(map, now + 100);
  Pump(service, players, now + 100);
  CHECK(host.map_board.members_size() == 2);
  CHECK(guest.map_board.members_size() == 2);
  CHECK(outsider.map_board.members_size() == 1);
  CHECK(outsider.map_board.members(0).member() == "outsider");
  host.Vitals(map, 1, now + 200);
  guest.Vitals(map, 1, now + 200);
  Pump(service, players, now + 200);
  CHECK(host.vitals_board.members_size() >= 2);
  CHECK(guest.vitals_board.members_size() >= 2);
  CHECK(outsider.vitals_board.members_size() <= 1);
  host.Propose({{map, {0x10014066}}}, now + 300);
  Pump(service, players, now + 300);
  CHECK(Killed(host, 0x10014066));
  CHECK(Killed(guest, 0x10014066));
  CHECK(!Killed(outsider, 0x10014066));
  // ACKs from each game have independent streams; no extra message
  // is required to converge the two copies of this world's log.
  Pump(service, players, now + 400);
  CHECK(Killed(guest, 0x10014066));
  return 0;
}

"""

TEST_ANCHOR = """int main() {
  const std::vector<std::pair<const char *, std::function<int()>>> tests{
"""
TEST_REPLACED = CPP_TEST + TEST_ANCHOR + """      {"IdenticalCoopBroadcastsKeepPartyWorldAndReliableDelivery",
       IdenticalCoopBroadcastsKeepPartyWorldAndReliableDelivery},
"""

def once(source, old, new, label):
    if source.count(old) != 1:
        raise ValueError("Pinned original YT1.3 source changed at " + label)
    return source.replace(old, new)

def rewrite(cpp, header, test):
    if "SendEncoded(Member&" in cpp or "IdenticalCoopBroadcastsKeepPartyWorld" in test:
        raise ValueError("Double application not allowed")
    if "YT130_COOP_RELIABILITY" not in cpp or "m_diagEnvelopes" not in header:
        raise ValueError("Original reliable Coop7 diagnostics must be staged first")
    if "NonHostedTeamEditsAreCoalescedAndStartStillWorks" not in test:
        raise ValueError("Original native world C++ functional stage must exist")
    cpp = once(cpp, SEND_BEFORE, SEND_AFTER, "SendTo and per-recipient ACK")
    cpp = once(cpp, ENTRY_BEFORE, ENTRY_AFTER, "SendEntries")
    cpp = once(cpp, BOARD_BEFORE, BOARD_AFTER, "SendBoards")
    header = once(header, H_BEFORE, H_AFTER, "SendEncoded declaration")
    test = once(test, TEST_ANCHOR, TEST_REPLACED, "independent C++ 3-party test")
    return cpp, header, test

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Expected exactly official YT v1.3.0 source commit")
    files = [root / p for p in (CPP, HEADER, TEST)]
    for rel, path in zip((CPP, HEADER, TEST), files):
        if git(root, "rev-parse", "HEAD:" + rel) != BLOBS[rel] or path.is_symlink():
            raise ValueError("Official source blob SHA mismatch / symlink: " + rel)
        if not git(root, "diff", "--", rel):
            raise ValueError("Required original staging missing: " + rel)
    changed = rewrite(*(p.read_text(encoding="utf-8") for p in files))
    for path, contents in zip(files, changed):
        path.write_text(contents, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_COOP7_SHARED_PROTOBUF_ENCODE_PER_BROADCAST_NATIVE_CPP_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_original_YT13_checkout", type=Path)
    apply(parser.parse_args().disposable_original_YT13_checkout)
