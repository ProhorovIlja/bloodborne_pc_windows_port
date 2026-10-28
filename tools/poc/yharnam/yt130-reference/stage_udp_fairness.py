#!/usr/bin/env python3
"""Source-pinned, bounded Qt UDP callback with queued lossless continuation.

Motivation: original 200-peer CI reported a 966,832 us continuous UDP callback
and 1,016,071 us gap between 50ms world ticks. The Qt loop must get a chance
to run its timers without dropping unprocessed incoming datagrams. Every
continuation checks the socket again and all original authentication remains.
"""
from pathlib import Path
import argparse
import subprocess
import stage_eventloop_timing as previous

PIN = previous.PIN
CPP = previous.CPP_FILE
HEADER = previous.HEADER_FILE
BLOBS = {CPP: previous.CPP_BLOB, HEADER: previous.HEADER_BLOB}

ORIGINAL_READ = previous.MEASURED_READ
if ORIGINAL_READ.count("    while (m_socket->hasPendingDatagrams()) {") != 1:
    raise RuntimeError("Original timing source changed unexpectedly")
FAIR_READ = ORIGINAL_READ.replace(
    "    while (m_socket->hasPendingDatagrams()) {",
    """    // A burst must not monopolize the Qt event loop: original unrestricted
    // processing blocked the 50ms world timer for nearly one second at 200 peers.
    // No discard, no packet reordering and the original admit/auth path remains.
    // The hard 128 datagram limit also bounds empty and malformed datagrams.
    while (m_socket->hasPendingDatagrams()) {
        if (diag_datagrams >= 128 ||
            (diag_datagrams >= 16 && (diag_datagrams % 16) == 0 &&
             busy.nsecsElapsed() >= 2'000'000)) {
            break;
        }""")
FAIR_READ = FAIR_READ.replace(
    "    ++m_diagReadBatches;",
    """    if (m_socket->hasPendingDatagrams() && !m_udpContinuationQueued) {
        // QUdpSocket readyRead is not guaranteed to re-emit just because a
        // callback returned with datagrams still pending. Queue exactly one
        // continuation with the object as its lifetime guard.
        m_udpContinuationQueued = true;
        QTimer::singleShot(0, this, [this] {
            m_udpContinuationQueued = false;
            OnReadyRead();
        });
    }
    ++m_diagReadBatches;""")
if FAIR_READ == ORIGINAL_READ or "m_udpContinuationQueued" not in FAIR_READ:
    raise RuntimeError("Fair UDP patch failed to produce its full callback")

HEADER_OLD = "    quint64 m_diagReadBatches = 0;"
HEADER_NEW = """    // Only the existing Qt link thread writes this, never shared between peers.
    bool m_udpContinuationQueued = false;
    quint64 m_diagReadBatches = 0;"""

def once(source, old, new, label):
    if source.count(old) != 1:
        raise ValueError("Original Qt source drift: " + label)
    return source.replace(old, new)

def rewrite(cpp, header):
    if "m_udpContinuationQueued" in cpp or "m_udpContinuationQueued" in header:
        raise ValueError("Double application of UDP fairness")
    if "RecordWire(raw, true)" not in cpp or "YT130_EVENTLOOP" not in cpp:
        raise ValueError("Original wire/timer instrumentation must run first")
    return (once(cpp, ORIGINAL_READ, FAIR_READ, "measured OnReadyRead"),
            once(header, HEADER_OLD, HEADER_NEW, "Qt event-loop diagnostics"))

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Source is not the pinned original official YT1.3")
    files = [root / CPP, root / HEADER]
    for name, file in zip((CPP, HEADER), files):
        if git(root, "rev-parse", "HEAD:" + name) != BLOBS[name]:
            raise ValueError("Wrong official Qt source blob: " + name)
        if file.is_symlink() or not git(root, "diff", "--", name):
            raise ValueError("Expected source-instrumented, not symlinked: " + name)
    out = rewrite(*(f.read_text(encoding="utf-8") for f in files))
    for file, source in zip(files, out):
        file.write_text(source, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_QT_UDP_FAIRNESS_128_PACKET_2MS_QUEUED_NO_DROP_STAGED")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_original_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_original_yt130_checkout)
