#!/usr/bin/env python3
"""Experimental fair reading of native YT1.3 Qt UDP (not a production pass).

At 64+ synthetic peers Qt world ticks are late when a single UDP readyRead
callback runs continuously. Limit that callback to 64 datagrams or 2 ms,
then explicitly re-drain from a receiver-owned Qt timer. Qt does not promise
a second readyRead when the first callback leaves datagrams in the socket.
Original packet handling, bytes, authorization and delivery are unchanged.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import stage_eventloop_timing as timing

PIN = timing.PIN
CPP_FILE, HEADER_FILE = timing.CPP_FILE, timing.HEADER_FILE
CPP_BLOB, HEADER_BLOB = timing.CPP_BLOB, timing.HEADER_BLOB
MAX_DATAGRAMS, MAX_READ_US, CONTINUATION_DELAY_MS = 64, 2000, 1
LOOP_ANCHOR = """    while (m_socket->hasPendingDatagrams()) {
        QByteArray raw;"""
LOOP_REPLACEMENT = """    // SHYT-V125-UDP-FAIR-NO-DROP: 64 datagrams or 2 ms per callback.
    // Qt readyRead is not promised again if incoming data was not drained.
    while (m_socket->hasPendingDatagrams()) {
        if (diag_datagrams >= 64 ||
            (diag_datagrams > 0 && busy.nsecsElapsed() >= 2'000'000LL)) {
            ++m_diagReadYields;
            if (!m_udpFairContinuationPending) {
                m_udpFairContinuationPending = true;
                QTimer::singleShot(1, this, [this] {
                    m_udpFairContinuationPending = false;
                    OnReadyRead();
                });
            }
            break;
        }
        QByteArray raw;"""
HEADER_ANCHOR = "    quint64 m_diagReadBatches = 0;"
HEADER_REPLACEMENT = """    // All read callbacks execute on the same Qt thread. Receiver-owned timer
    // is cancelled by Qt at object destruction; never leave an unowned lambda.
    bool m_udpFairContinuationPending = false;
    quint64 m_diagReadYields = 0;
    quint64 m_diagReadBatches = 0;"""
LOG_ANCHOR = '            << " read_datagrams=" << m_diagReadDatagrams'
LOG_REPLACEMENT = ('            << " read_datagrams=" << m_diagReadDatagrams\n'
                   '            << " read_yields=" << m_diagReadYields')
RESET_ANCHOR = "        m_diagReadBatches = m_diagReadDatagrams = m_diagReadBusyUs = 0;"
RESET_REPLACEMENT = """        m_diagReadYields = 0;
        m_diagReadBatches = m_diagReadDatagrams = m_diagReadBusyUs = 0;"""


def rewrite(cpp: str, header: str) -> tuple[str, str]:
    if cpp.count(timing.MEASURED_READ) != 1:
        raise ValueError("Expected exactly one instrumented Qt receive callback")
    if "SHYT-V125-UDP-FAIR-NO-DROP" in cpp or "m_udpFairContinuationPending" in header:
        raise ValueError("Already staged V125 or duplicate receive callback")
    def one(value: str, before: str, after: str, role: str) -> str:
        if value.count(before) != 1:
            raise ValueError("Pinned Qt V125 source changed: " + role)
        return value.replace(before, after, 1)
    new_read = one(timing.MEASURED_READ, LOOP_ANCHOR, LOOP_REPLACEMENT, "socket loop")
    cpp = cpp.replace(timing.MEASURED_READ, new_read, 1)
    cpp = one(cpp, LOG_ANCHOR, LOG_REPLACEMENT, "event-loop 5s output")
    cpp = one(cpp, RESET_ANCHOR, RESET_REPLACEMENT, "event-loop 5s reset")
    header = one(header, HEADER_ANCHOR, HEADER_REPLACEMENT, "Qt read continuation flag")
    if "RecordWire(raw, true)" not in cpp or "Apply(m_world.Tick" not in cpp:
        raise ValueError("Lost original wire counter or 50ms world updates")
    if cpp.count("QTimer::singleShot(1, this, [this]") != 1:
        raise ValueError("Missing exactly-one receiver-owned continuation")
    return cpp, header


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong official YT1.3 source revision")
    for path, blob in ((CPP_FILE, CPP_BLOB), (HEADER_FILE, HEADER_BLOB)):
        if git(root, "rev-parse", "HEAD:" + path) != blob:
            raise ValueError("Wrong original pinned Qt blob: " + path)
    cpp_path, header_path = root / CPP_FILE, root / HEADER_FILE
    cpp, header = rewrite(cpp_path.read_text(encoding="utf-8"),
                          header_path.read_text(encoding="utf-8"))
    cpp_path.write_bytes(cpp.encode("utf-8"))
    header_path.write_bytes(header.encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("SHYT_V125_QT_BOUNDED_RECEIVE_WITH_EXPLICIT_NO_DROP_REQUEUE_STAGED_ONLY")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_original_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_original_yt130_checkout)
