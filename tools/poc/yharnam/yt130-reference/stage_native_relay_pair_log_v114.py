#!/usr/bin/env python3
"""V114: original native Qt server data-relay fast path, no debug hash per frame.

The upstream LinkServer constructs Hub() with 20 verbose "first frame" log
lines per directed pair. Every game datagram pays a QHash pair lookup and
increment even AFTER the 20 lines. In a real multi-team server, this is
unnecessary CPU and startup logging overhead. Set only the real Qt server
hub to pair_lines=0; maintain default logging for standalone Hub and tests.
Preserve all routing, authentication, encrypted packets, drops and diagnostics.
Only a pinned disposable original source checkout is written.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
LINK_H = "server/src/link_server.h"
HUB_CPP = "server/src/server_link.cpp"
HUB_TEST = "server/tests/test_server_link.cpp"
BLOBS = {
    LINK_H: "4530df9be35e161cd4e4fd56fe1f1696bb8b407b",
    HUB_CPP: "eca0980de1e72177c38e1a0e3e613e9a97f13442",
    HUB_TEST: "454f5575dcfe1b45ee56b0b42353f34aaee2556d",
}
MARKER = "SHYT-V114-NATIVE-RELAY-NO-PER-PAIR-DEBUG-HASH"

HEADER_OLD = "    ServerLink::Hub m_link;"
HEADER_NEW = """    // SHYT-V114-NATIVE-RELAY-NO-PER-PAIR-DEBUG-HASH
    // Actual shadNet UDP relay: skip per-game-datagram QHash bookkeeping
    // and synchronous first-20-frame-pair log bursts. The public Hub()
    // default stays unchanged for full diagnostics in original tests.
    ServerLink::Hub m_link{3000, 60000, 10000, 0, 12000};"""

HUB_OLD = """    // The first frames between each pair: a stalled join shows which went.
    const quint64 count = ++pair_frames[qMakePair(sender.endpoint.Key(), target->endpoint.Key())];
    if (count <= static_cast<quint64>(pair_lines)) {
        result.log.append(QStringLiteral("server link: %1 -> %2 #%3: %4 bytes, vport %5 -> %6, %7")
                              .arg(Name(sender), Name(*target))
                              .arg(count)
                              .arg(data->frame.size() - 4)
                              .arg(Vport(data->frame, 0))
                              .arg(Vport(data->frame, 2))
                              .arg(Head(data->frame)));
    }"""
HUB_NEW = """    // SHYT-V114-NATIVE-RELAY-NO-PER-PAIR-DEBUG-HASH:
    // Never allocate or update pair_frames on the actual high-rate server
    // when pair diagnostic logging is disabled. The original Hub constructor
    // still allows explicit per-pair debugging in test tools.
    if (pair_lines > 0) {
        const quint64 count =
            ++pair_frames[qMakePair(sender.endpoint.Key(), target->endpoint.Key())];
        if (count <= static_cast<quint64>(pair_lines)) {
            result.log.append(QStringLiteral("server link: %1 -> %2 #%3: %4 bytes, vport %5 -> %6, %7")
                                  .arg(Name(sender), Name(*target))
                                  .arg(count)
                                  .arg(data->frame.size() - 4)
                                  .arg(Vport(data->frame, 0))
                                  .arg(Vport(data->frame, 2))
                                  .arg(Head(data->frame)));
        }
    }"""

TEST_ANCHOR = """  CHECK(lines == 2);

  // A ping comes back as a pong with the same body."""
TEST_REPLACE = """  CHECK(lines == 2);

  // SHYT-V114-NATIVE-RELAY-NO-PER-PAIR-DEBUG-HASH: the actual server uses
  // the zero-log Hub. Suppressing only debug bookkeeping must not touch
  // encrypted datagrams, sender identity, replay protection or routing.
  Net no_pair_debug(3000, 60000, 10000, 0);
  no_pair_debug.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  no_pair_debug.Receive(Ada, HelloFrom("Ada"), 0);
  for (int index = 0; index < 100; ++index) {
    const auto sample = no_pair_debug.Receive(
        Kaniel, Encode(Data{VirtualEndpointOf("Ada"), GameFrame}), 100 + index);
    const auto delivered = SentTo(sample, Ada);
    CHECK(delivered.size() == 1 && sample.sends.size() == 1);
    CHECK(sample.log.isEmpty()); // no synchronous per-pair message
    const auto forwarded = DecodeData(delivered[0]);
    CHECK(forwarded && forwarded->peer == VirtualEndpointOf("Kaniel") &&
          forwarded->frame == GameFrame);
  }
  CHECK(no_pair_debug.unopened == 0);
  // The original default diagnostic Hub still emits its first frame logs.
  // (Verified by the untouched CHECK(lines == 2) and initial Relays() case.)

  // A ping comes back as a pong with the same body."""

def replace_once(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f"{MARKER}: source anchor drift for {label}: {count}")
    return src.replace(old, new, 1)

def rewrite(files: dict[str, str]) -> dict[str, str]:
    if set(files) != set(BLOBS):
        raise ValueError("V114 requires all three real native Qt files")
    if any(MARKER in files[path] for path in files):
        raise ValueError("V114 must not be staged twice")
    link = replace_once(files[LINK_H], HEADER_OLD, HEADER_NEW, "real server Hub member")
    cpp = replace_once(files[HUB_CPP], HUB_OLD, HUB_NEW, "game data debug fast path")
    tests = replace_once(files[HUB_TEST], TEST_ANCHOR, TEST_REPLACE,
                         "actual original relays regression")
    return {LINK_H: link, HUB_CPP: cpp, HUB_TEST: tests}

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("V114 expects pinned original YT1.3 Git commit")
    paths = {rel: root / rel for rel in BLOBS}
    for rel, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"V114 unsafe/missing source: {rel}")
        if git(root, "rev-parse", "HEAD:" + rel) != BLOBS[rel]:
            raise ValueError(f"V114 untrusted original Git blob: {rel}")
        # Existing instrumentation stages link_server.h only. We do not
        # overwrite any old server_link.cpp or test_server_link.cpp edits.
        if rel == HUB_TEST and git(root, "diff", "--", rel):
            raise ValueError(f"V114 unexpected previous Qt C++ unit-test patch: {rel}")
    # Existing V108 3-hostile topology is intentionally staged in this file
    # before V114. Never silently erase or bypass that authorization branch.
    if "SHYT-V108-MULTI-INVADER-ORIGINAL-SERVER" not in paths[HUB_CPP].read_text(encoding="utf-8"):
        raise ValueError("V114 requires original V108 hostile topology changes")
    candidate = rewrite({rel: p.read_text(encoding="utf-8")
                         for rel, p in paths.items()})
    for rel, path in paths.items():
        path.write_text(candidate[rel], encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V114_ORIGINAL_RELAY_PAIR_LOG_FASTPATH_STAGED_NOT_CAPACITY_PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_native_relay_pair_log_v114.py ORIGINAL_YT13_CLONE")
    stage(Path(sys.argv[1]))
