#!/usr/bin/env python3
"""Coalesce full legacy/nonHosted LobbyState snapshots based on live link count.

Source observed: at 200 original YT1.3 synthetic connections, LobbyState made
218.2 MiB of 221.4 MiB of pre-retry Coop(7) protobuf payloads (98.57%).
No protocol/visibility change: keep full lobby state, only defer redundant
intermediate snapshots during churn. Initial LobbyHello and TeamStart remain
immediate in original C++, with 50ms cadence for fewer than 64 connections.
"""
from pathlib import Path
import argparse
import subprocess
import stage_lobby_dedupe as dedupe

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP = "server/src/bloodborne_world.cpp"
TEST = "server/tests/test_bloodborne_world.cpp"
BLOBS = {
    CPP: "eca8c30d6fb78099b0f64a52388fd7d65f926e19",
    TEST: "2ec55d02101545723e9889bebe83d8b1d531a1c7",
}
OLD_TICK = """    if (lobby_changed && (!hosted.enabled || now_ms - lobby_sent_ms >= hosted.lobby_interval_ms)) {
        SendLobby(now_ms);
    }"""
NEW_TICK = """    // Non-Hosted still publishes the ORIGINAL full lobby for compatibility,
    // but sending an O(all players) snapshot after each 50ms churn tick
    // creates most of our Coop(7) bytes at 200 concurrent clients.
    // Never delay direct OnLobbyHello initial state or synchronous TeamStart.
    // Keep the small-party latency of original YT, preserve Hosted's own rules.
    const qint64 nonhosted_lobby_interval_ms =
        members.size() >= 128 ? 500 : (members.size() >= 64 ? 250 : 0);
    const qint64 lobby_interval_ms =
        hosted.enabled ? hosted.lobby_interval_ms : nonhosted_lobby_interval_ms;
    if (lobby_changed && now_ms - lobby_sent_ms >= lobby_interval_ms) {
        SendLobby(now_ms);
    }"""

ORIGINAL_JOIN_STATE = """    if (arrived) {
        // Its state even when nothing changed for the others.
        bbcoop::Envelope envelope;
        *envelope.mutable_lobby_state() = lobby.StateFor(member.lobby);
        SendTo(member, envelope, now_ms);
    }"""
CACHED_JOIN_STATE = """    if (arrived) {
        // Its state even when nothing changed for the others.
        bbcoop::Envelope envelope;
        *envelope.mutable_lobby_state() = lobby.StateFor(member.lobby);
        // First connection's state is still sent immediately. The next
        // global nonHosted snapshot need not repeat those exact bytes.
        if (!hosted.enabled) {
            lobby_sent[member.lobby] = envelope.lobby_state().SerializeAsString();
        }
        SendTo(member, envelope, now_ms);
    }"""

CPP_TEST = r"""int NonHostedFullLobbyIsAdaptiveWithoutDelayingFirstHello() {
  Service service{{}};
  const qint64 now = 1'000'000;
  std::vector<std::unique_ptr<Game>> ownership;
  std::vector<Game *> players;
  const auto add = [&](int begin, int end, qint64 at) {
    for (int i = begin; i < end; ++i) {
      std::string name = i == 0 ? "lead" :
                         i == 1 ? "guest" : "hunter" + std::to_string(i);
      auto client = std::make_unique<Game>(1000 + i, std::move(name), 100 + i);
      client->Hello(at);
      client->LobbyHello(false, at);
      players.push_back(client.get());
      ownership.push_back(std::move(client));
    }
  };
  add(0, 65, now);
  Pump(service, players, now);
  CHECK(players.size() == 65);
  CHECK(players[0]->welcome && players[0]->welcome->accepted());
  CHECK(players[1]->lobby_states >= 1); // Immediate first hello unaffected.
  const int before = players[1]->lobby_states;
  players[0]->Team(bbcoop::TeamRequest::CREATE, now + 100);
  players[0]->Team(bbcoop::TeamRequest::INVITE, now + 100, "guest");
  Pump(service, players, now + 100);
  CHECK(players[1]->lobby_states == before); // >=64: no 50ms fanout.
  Pump(service, players, now + 300);
  CHECK(players[1]->lobby_states > before); // 250ms coalesced snapshot.
  CHECK(players[1]->lobby.invites_size() == 1);
  const int before_big = players[1]->lobby_states;
  add(65, 130, now + 350);
  Pump(service, players, now + 350);
  CHECK(players.size() == 130);
  CHECK(players.back()->lobby_states >= 1); // Late arrival gets own state now.
  CHECK(players[1]->lobby_states == before_big);
  Pump(service, players, now + 700);
  CHECK(players[1]->lobby_states == before_big); // >=128: wait 500ms.
  Pump(service, players, now + 810);
  CHECK(players[1]->lobby_states > before_big);
  // Existing party and invitation still present in final full snapshot.
  CHECK(players[1]->lobby.invites_size() == 1);
  return 0;
}

"""
OLD_TEST = """int main() {
  const std::vector<std::pair<const char *, std::function<int()>>> tests{
"""
NEW_TEST = CPP_TEST + OLD_TEST + """      {"NonHostedFullLobbyIsAdaptiveWithoutDelayingFirstHello",
       NonHostedFullLobbyIsAdaptiveWithoutDelayingFirstHello},
"""

def once(source, old, new, label):
    if source.count(old) != 1:
        raise ValueError("Pinned original YT1.3 source drift: " + label)
    return source.replace(old, new)

def rewrite(cpp, test):
    if "nonhosted_lobby_interval_ms" in cpp or "NonHostedFullLobbyIsAdaptive" in test or "first-join cache" in cpp:
        raise ValueError("Already staged")
    if "NonHostedTeamEditsAreCoalescedAndStartStillWorks" not in test:
        raise ValueError("Native first-join and synchronous TeamStart test missing")
    if "void Service::SendLobby(qint64 now_ms)" not in cpp or        "void Service::OnLobbyHello(" not in cpp or        "void Service::Settle(" not in cpp:
        raise ValueError("No exact original lobby path")
    cpp = once(cpp, OLD_TICK, NEW_TICK, "world Tick throttle")
    cpp = once(cpp, ORIGINAL_JOIN_STATE, CACHED_JOIN_STATE,
               "original immediate lobby Hello")
    # Stage_lobby_dedupe.py, applied earlier, ALREADY compares the complete
    # original state bytes for all recipients. Only the first-join cache was
    # missing. Require the earlier change rather than stage it twice.
    if cpp.count(dedupe.AFTER) != 1:
        raise ValueError("Required existing nonHosted full-snapshot dedupe missing")
    return cpp, once(test, OLD_TEST, NEW_TEST, "native 65/130 member test")

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Only exact original official YT1.3 checkout")
    files = [root / CPP, root / TEST]
    for rel, path in zip((CPP, TEST), files):
        if git(root, "rev-parse", "HEAD:" + rel) != BLOBS[rel] or path.is_symlink():
            raise ValueError("Original source blob mismatch / symlink: " + rel)
        if not git(root, "diff", "--", rel):
            raise ValueError("Original instrumented & coalesced C++ source missing: " + rel)
    changed = rewrite(*(p.read_text(encoding="utf-8") for p in files))
    for path, value in zip(files, changed):
        path.write_text(value, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_NONHOSTED_FULL_LOBBY_250_500MS_ADAPTIVE_COALESCE_CPP_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_official_yt13_checkout", type=Path)
    apply(parser.parse_args().disposable_official_yt13_checkout)
