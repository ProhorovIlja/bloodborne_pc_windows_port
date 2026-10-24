#!/usr/bin/env python3
"""Fail-closed QoS-only C++ optimization for Yharnam Together's shadNet relay.

No packet filtering, protocol, security, relay destination, counter or
world-ownership behavior is altered. Hot data packets avoid a QByteArray
substring allocation for the SHAD magic, and diagnostic pair counters stop
updating once the first N messages have been logged. Original GPL notice and
authors are preserved. Real performance benefit is not claimed until measured.
"""
from __future__ import annotations
import argparse
from pathlib import Path

CPP = "server/src/server_link.cpp"
SIGNATURE = "SHYT-SERVER-RELAY-PERF-V45"
INCLUDE = '#include <algorithm>\n'
NEEDLE = 'frame.mid(4, 4) != "SHAD"'
PAIR_OLD = '''    // The first frames between each pair: a stalled join shows which went.
    const quint64 count = ++pair_frames[qMakePair(sender.endpoint.Key(), target->endpoint.Key())];
    if (count <= static_cast<quint64>(pair_lines)) {
        result.log.append(QStringLiteral("server link: %1 -> %2 #%3: %4 bytes, vport %5 -> %6, %7")
                              .arg(Name(sender), Name(*target))
                              .arg(count)
                              .arg(data->frame.size() - 4)
                              .arg(Vport(data->frame, 0))
                              .arg(Vport(data->frame, 2))
                              .arg(Head(data->frame)));
    }
'''
PAIR_NEW = '''    // SHYT-SERVER-RELAY-PERF-V45: only the first pair_lines are diagnostic.
    // Never increment this QHash counter after reaching the configured limit.
    // With pair_lines == 0, skip pair-key construction and map operations.
    // All forwarded datagrams, routing/ownership checks and byte counters above
    // remain byte-for-byte identical to the pinned server code.
    if (pair_lines > 0) {
        auto& count = pair_frames[qMakePair(sender.endpoint.Key(), target->endpoint.Key())];
        if (count < static_cast<quint64>(pair_lines)) {
            ++count;
            result.log.append(QStringLiteral("server link: %1 -> %2 #%3: %4 bytes, vport %5 -> %6, %7")
                                  .arg(Name(sender), Name(*target))
                                  .arg(count)
                                  .arg(data->frame.size() - 4)
                                  .arg(Vport(data->frame, 0))
                                  .arg(Vport(data->frame, 2))
                                  .arg(Head(data->frame)));
        }
    }
'''


def replace_once(text: str, old: str, new: str, purpose: str) -> str:
    hits = text.count(old)
    if hits != 1:
        raise ValueError(f"V45 pinned {purpose} anchor changed: wanted one, found {hits}")
    return text.replace(old, new, 1)


def transform(source: str) -> str:
    if SIGNATURE in source:
        raise ValueError("V45 is already applied")
    if "SPDX-License-Identifier: GPL-2.0-or-later" not in source:
        raise ValueError("Upstream license header missing: do not erase authorship")
    if "result.sends.append({target->endpoint, Encode(Data{sender.virtual_endpoint, *routed})});" not in source:
        raise ValueError("Relay data path changed; abort optimization")
    source = replace_once(source, INCLUDE, "#include <algorithm>\n#include <cstring>\n", "cstring include")
    source = replace_once(source, NEEDLE,
                          'std::memcmp(frame.constData() + 4, "SHAD", 4) != 0',
                          "SHAD header comparison")
    source = replace_once(source, PAIR_OLD, PAIR_NEW, "diagnostic pair counters")
    return source


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("server_link_cpp", type=Path)
    args = ap.parse_args()
    original = args.server_link_cpp.read_text("utf-8")
    args.server_link_cpp.write_text(transform(original), "utf-8")
    print("SHYT_V45_PINNED_NATIVE_SHADNET_HOTPATH_PASS")


if __name__ == "__main__":
    main()
