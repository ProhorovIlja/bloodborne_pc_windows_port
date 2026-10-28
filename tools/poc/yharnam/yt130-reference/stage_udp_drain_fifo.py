#!/usr/bin/env python3
"""Source-pinned Qt UDP full socket drain / bounded handler queue on YT 1.3.

Never leave pending kernel datagrams unread when returning from readyRead.
Preserve packet FIFO and the original HandleLink admission/routing code.
Only expensive packet processing is sliced across zero-delay queued callbacks.
On rare bounded-queue overflow, process oldest FIFO item in-place, never
silently discard or reorder an authenticated packet; record overflow evidence.
"""
import argparse
from pathlib import Path
import subprocess
import stage_eventloop_timing as previous

PIN = previous.PIN
CPP = previous.CPP_FILE
HEADER = previous.HEADER_FILE
BLOBS = {CPP: previous.CPP_BLOB, HEADER: previous.HEADER_BLOB}

ORIGINAL_READ = previous.MEASURED_READ
OLD_BODY = """        if (raw.isEmpty())
            continue;

        // The games' link only (phase 9: no STUN, nothing else on this port).
        if (ServerLink::KindOf(raw)) {
            HandleLink(raw, sender, senderPort);
        }
    }
    ++m_diagReadBatches;"""
NEW_BODY = """        if (raw.isEmpty())
            continue;

        // Drain the kernel UDP socket completely in the Qt readyRead callback.
        // HandleLink may do sign-in, world changes and fan-out. Move that
        // expensive work to an in-order, time-sliced application FIFO.
        if (ServerLink::KindOf(raw)) {
            // If a packet burst exceeds this bounded queue, process the
            // oldest packet here to make space. Keep FIFO ordering, never
            // silently drop authenticated reliable data, and record pressure
            // so a high-load pass cannot conceal overload.
            while (!m_udpPending.empty() &&
                   (m_udpPending.size() >= MaxUdpQueuePackets ||
                    m_udpPendingBytes + static_cast<size_t>(raw.size()) > MaxUdpQueueBytes)) {
                ++m_udpQueuePressure;
                auto old = std::move(m_udpPending.front());
                m_udpPending.pop_front();
                m_udpPendingBytes -= static_cast<size_t>(old.bytes.size());
                HandleLink(old.bytes, old.sender, old.port);
            }
            m_udpPendingBytes += static_cast<size_t>(raw.size());
            m_udpPending.push_back({std::move(raw), sender, senderPort});
            m_udpMaxPending = std::max(m_udpMaxPending, m_udpPending.size());
        }
    }
    if (!m_udpPending.empty() && !m_udpDrainQueued) {
        m_udpDrainQueued = true;
        QTimer::singleShot(0, this, [this] { DrainUdpPending(); });
    }
    ++m_diagReadBatches;"""

NEW_METHOD = """
void LinkServer::DrainUdpPending() {
    m_udpDrainQueued = false;
    QElapsedTimer busy;
    busy.start();
    size_t handled = 0;
    while (!m_udpPending.empty()) {
        // Time-slice expensive Hub/world updates, not the socket drain.
        if (handled >= 128 ||
            (handled >= 16 && (handled % 16) == 0 &&
             busy.nsecsElapsed() >= 2'000'000)) {
            break;
        }
        auto next = std::move(m_udpPending.front());
        m_udpPending.pop_front();
        m_udpPendingBytes -= static_cast<size_t>(next.bytes.size());
        HandleLink(next.bytes, next.sender, next.port);
        ++handled;
    }
    if (!m_udpPending.empty() && !m_udpDrainQueued) {
        m_udpDrainQueued = true;
        QTimer::singleShot(0, this, [this] { DrainUdpPending(); });
    }
    Busy(busy);
}
"""

OLD_H = """    quint64 m_diagReadBatches = 0;"""
NEW_H = """    // FIFO is owned only by the original Qt link thread. No peer IDs or
    // decrypted payloads are logged; pending datagrams never go to disk.
    struct PendingUdp {
        QByteArray bytes;
        QHostAddress sender;
        uint16_t port = 0;
    };
    static constexpr size_t MaxUdpQueuePackets = 16384;
    static constexpr size_t MaxUdpQueueBytes = 32 << 20;
    std::deque<PendingUdp> m_udpPending;
    size_t m_udpPendingBytes = 0;
    size_t m_udpMaxPending = 0;
    quint64 m_udpQueuePressure = 0;
    bool m_udpDrainQueued = false;
    quint64 m_diagReadBatches = 0;"""

OLD_METHOD_DECL = """    void OnReadyRead();
    void OnLinkTick();"""
NEW_METHOD_DECL = """    void OnReadyRead();
    void DrainUdpPending();
    void OnLinkTick();"""

OLD_INCLUDES = """#include <map>
#include <memory>"""
NEW_INCLUDES = """#include <deque>
#include <map>
#include <memory>"""

OLD_EVENTLOG = """            << " read_datagrams=" << m_diagReadDatagrams"""
NEW_EVENTLOG = """            << " udp_queue_max=" << m_udpMaxPending
            << " udp_queue_pressure=" << m_udpQueuePressure
            << " read_datagrams=" << m_diagReadDatagrams"""

OLD_RESET = """        m_diagReadBatches = m_diagReadDatagrams = m_diagReadBusyUs = 0;"""
NEW_RESET = """        m_udpMaxPending = m_udpPending.size();
        m_udpQueuePressure = 0;
        m_diagReadBatches = m_diagReadDatagrams = m_diagReadBusyUs = 0;"""

def once(source, before, after, label):
    if source.count(before) != 1:
        raise ValueError("Pinned original staged Qt source drift: " + label)
    return source.replace(before, after)

def rewrite(cpp, header):
    if "DrainUdpPending" in cpp or "m_udpPending" in header:
        raise ValueError("FIFO fairness already installed")
    if "YT130_EVENTLOOP" not in cpp or "RecordWire(raw, true)" not in cpp:
        raise ValueError("Source instrumentation must be staged before FIFO")
    if cpp.count(ORIGINAL_READ) != 1:
        raise ValueError("Original measured readyRead changed")
    cpp = once(cpp, OLD_BODY, NEW_BODY, "kernel socket drain and queue")
    cpp = once(cpp, "void LinkServer::HandleLink(", NEW_METHOD + "\nvoid LinkServer::HandleLink(", "new drain method")
    cpp = once(cpp, OLD_EVENTLOG, NEW_EVENTLOG, "source telemetry fields")
    cpp = once(cpp, OLD_RESET, NEW_RESET, "source telemetry reset")
    header = once(header, OLD_INCLUDES, NEW_INCLUDES, "bounded deque include")
    header = once(header, OLD_H, NEW_H, "bounded pending state")
    header = once(header, OLD_METHOD_DECL, NEW_METHOD_DECL, "Qt callback declaration")
    return cpp, header

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Exact official YT 1.3 commit required")
    files = [root / CPP, root / HEADER]
    for name, file in zip((CPP, HEADER), files):
        if git(root, "rev-parse", "HEAD:" + name) != BLOBS[name]:
            raise ValueError("Original Qt source SHA drift: " + name)
        if file.is_symlink() or not git(root, "diff", "--", name):
            raise ValueError("Missing source-pinned instrumentation or symlink: " + name)
    changed = rewrite(*(f.read_text(encoding="utf-8") for f in files))
    for file, result in zip(files, changed):
        file.write_text(result, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_UDP_DRAIN_KERNEL_FULLY_WITH_BOUNDED_FIFO_TIMESLICED_NO_DROP")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_official_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_official_yt130_checkout)
