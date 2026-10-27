#!/usr/bin/env python3
"""Source-pinned EXPERIMENT: drain kernel UDP socket, process auth/game FIFO in slices.

Unlike rejected PR22, never leaves unread datagrams trapped in QUdpSocket:
readyRead is ALWAYS fully drained before processing bounded queue work.
Bound memory (16k packets / 32 MiB) and disclose drops, never silently
invent success. No change to wire format, crypto, authentication or world.
An isolated alternative to evaluate AGAINST unchanged PR37 at 1000 players.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import stage_eventloop_timing as baseline

PIN = baseline.PIN
CPP_BLOB = baseline.CPP_BLOB
HEADER_BLOB = baseline.HEADER_BLOB

OLD_READ = baseline.MEASURED_READ
OLD_HANDLE = """        if (ServerLink::KindOf(raw)) {
            HandleLink(raw, sender, senderPort);
        }"""
NEW_HANDLE = """        if (ServerLink::KindOf(raw)) {
            const qint64 needed = static_cast<qint64>(raw.size());
            if (m_udpPending.size() >= 16384 ||
                m_udpPendingBytes + needed > 32LL * 1024 * 1024) {
                ++m_udpOverloadDrops;
            } else {
                m_udpPendingBytes += needed;
                m_udpPending.push_back(QueuedUdp{std::move(raw), sender, senderPort});
                m_udpMaxPending = std::max(
                    m_udpMaxPending, static_cast<quint64>(m_udpPending.size()));
            }
        }"""

DISPATCH = """void LinkServer::DrainPendingUdp() {
    if (m_udpDraining)
        return; // the original QObject event loop owns the queue
    m_udpDraining = true;
    QElapsedTimer work;
    work.start();
    int handled = 0;
    // Separate the expensive encrypted/authenticated game packet HandleLink
    // from the socket read notifier. Preserve FIFO within the same server.
    while (!m_udpPending.empty() && handled < 128 &&
           work.nsecsElapsed() < 2'000'000LL) {
        QueuedUdp item = std::move(m_udpPending.front());
        m_udpPending.pop_front();
        m_udpPendingBytes -= static_cast<qint64>(item.body.size());
        HandleLink(item.body, item.sender, item.port);
        ++handled;
    }
    ++m_udpSlices;
    m_udpHandled += handled;
    m_udpMaxSliceUs = std::max(
        m_udpMaxSliceUs, static_cast<quint64>(work.nsecsElapsed() / 1000));
    m_udpDraining = false;
    Busy(work);
    // Never depend on Qt re-emitting readyRead for data already read:
    // one 1-ms queued continuation lets the original 50-ms timer execute.
    if (!m_udpPending.empty() && !m_udpDrainQueued) {
        m_udpDrainQueued = true;
        QTimer::singleShot(1, this, [this] {
            m_udpDrainQueued = false;
            DrainPendingUdp();
        });
    }
}"""

OLD_LOG = """            << " late_world_ticks=" << m_diagLateWorldTicks;"""
NEW_LOG = """            << " late_world_ticks=" << m_diagLateWorldTicks;
        qInfo().nospace().noquote()
            << "YT130_UDP_FAIR_QUEUE slices=" << m_udpSlices
            << " handled=" << m_udpHandled
            << " max_slice_us=" << m_udpMaxSliceUs
            << " max_queued=" << m_udpMaxPending
            << " overload_drops=" << m_udpOverloadDrops
            << " queued=" << m_udpPending.size();"""

RESET = """        m_udpSlices = m_udpHandled = m_udpMaxSliceUs = 0;
        m_udpMaxPending = m_udpOverloadDrops = 0;
"""

HEADER_FIELDS = """    // Owned by original single Qt link thread. No worker touches game state.
    struct QueuedUdp {
        QByteArray body;
        QHostAddress sender;
        uint16_t port;
    };
    std::deque<QueuedUdp> m_udpPending;
    qint64 m_udpPendingBytes = 0;
    bool m_udpDraining = false;
    bool m_udpDrainQueued = false;
    quint64 m_udpSlices = 0;
    quint64 m_udpHandled = 0;
    quint64 m_udpMaxSliceUs = 0;
    quint64 m_udpMaxPending = 0;
    quint64 m_udpOverloadDrops = 0;
"""

def replace_one(source: str, old: str, new: str, where: str) -> str:
    if source.count(old) != 1:
        raise ValueError("Expected exact staged server source once: " + where)
    return source.replace(old, new)

def patch_text(cpp: str, header: str) -> tuple[str, str]:
    if cpp.count(OLD_READ) != 1 or header.count(baseline.HEADER_NEW) != 1:
        raise ValueError("Not the pinned post-eventloop, wire-instrumented source")
    if "YT130_UDP_FAIR_QUEUE" in cpp or "m_udpPending" in header:
        raise ValueError("Already staged or conflicting UDP reader")
    if OLD_READ.count(OLD_HANDLE) != 1:
        raise ValueError("Original source callback drift")
    new_read = OLD_READ.replace(OLD_HANDLE, NEW_HANDLE)
    new_read = replace_one(new_read, "    Busy(busy);\n}",
                           "    Busy(busy);\n    DrainPendingUdp();\n}",
                           "leave read notifier after full socket drain")
    cpp = cpp.replace(OLD_READ, new_read + "\n\n" + DISPATCH)
    cpp = replace_one(cpp, OLD_LOG, NEW_LOG, "eventloop timing metrics")
    cpp = replace_one(cpp,
                      "        m_diagMaxWorldGapUs = m_diagLateWorldTicks = 0;\n",
                      "        m_diagMaxWorldGapUs = m_diagLateWorldTicks = 0;\n" + RESET,
                      "5s queue diagnostics reset")
    header = replace_one(header, "#include <map>\n",
                         "#include <deque>\n#include <map>\n#include <utility>\n",
                         "std::deque FIFO include")
    header = replace_one(header, "    void OnReadyRead();\n",
                         "    void OnReadyRead();\n    void DrainPendingUdp();\n",
                         "original QObject class callback")
    header = replace_one(header, "    Database m_db;",
                         HEADER_FIELDS + "    Database m_db;",
                         "single Qt world instance")
    return cpp, header

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong exact original official YT1.3 commit")
    for path, blob in (("server/src/link_server.cpp", CPP_BLOB),
                       ("server/src/link_server.h", HEADER_BLOB)):
        if git(root, "rev-parse", "HEAD:" + path) != blob:
            raise ValueError("Original YT1.3 source blob changed")
    c, h = root / "server/src/link_server.cpp", root / "server/src/link_server.h"
    cpp, header = patch_text(c.read_text(encoding="utf-8"), h.read_text(encoding="utf-8"))
    c.write_text(cpp, encoding="utf-8")
    h.write_text(header, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_FAIR_UDP_BUFFERED_FULL_SOCKET_DRAIN_EXPERIMENT_ONLY_NOT_DEPLOY")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_original_source_checkout", type=Path)
    apply(parser.parse_args().disposable_original_source_checkout)
