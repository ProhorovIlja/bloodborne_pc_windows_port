#!/usr/bin/env python3
"""Instrument Qt event-loop starvation without changing official UDP behavior.

Pinned original YT1.3.0 LinkServer source, staged ONLY on a disposable Qt
checkout already source-patched by PR30. Specifically NO socket loop limits,
read order changes, packet drops, retransmit timing, gameplay or authentication
changes. Windowed 5s aggregate counters contain no player identifiers.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP_FILE = "server/src/link_server.cpp"
CPP_BLOB = "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8"
HEADER_FILE = "server/src/link_server.h"
HEADER_BLOB = "4530df9be35e161cd4e4fd56fe1f1696bb8b407b"

ORIGINAL_READ = """void LinkServer::OnReadyRead() {
    QElapsedTimer busy;
    busy.start();
    while (m_socket->hasPendingDatagrams()) {
        QByteArray raw;
        raw.resize(static_cast<int>(m_socket->pendingDatagramSize()));
        QHostAddress sender;
        uint16_t senderPort = 0;
        m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);

        if (raw.isEmpty())
            continue;

        // The games' link only (phase 9: no STUN, nothing else on this port).
        if (ServerLink::KindOf(raw)) {
            HandleLink(raw, sender, senderPort);
        }
    }
    Busy(busy);
}"""

MEASURED_READ = """void LinkServer::OnReadyRead() {
    QElapsedTimer busy;
    busy.start();
    quint64 diag_datagrams = 0;
    while (m_socket->hasPendingDatagrams()) {
        QByteArray raw;
        raw.resize(static_cast<int>(m_socket->pendingDatagramSize()));
        QHostAddress sender;
        uint16_t senderPort = 0;
        m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);
        ++diag_datagrams; // source processing identical; no fairness/drop change

        if (raw.isEmpty())
            continue;

        // The games' link only (phase 9: no STUN, nothing else on this port).
        if (ServerLink::KindOf(raw)) {
            HandleLink(raw, sender, senderPort);
        }
    }
    ++m_diagReadBatches;
    m_diagReadDatagrams += diag_datagrams;
    m_diagMaxReadBatchDatagrams = std::max(m_diagMaxReadBatchDatagrams, diag_datagrams);
    const quint64 diag_us = static_cast<quint64>(busy.nsecsElapsed() / 1000);
    m_diagReadBusyUs += diag_us;
    m_diagMaxReadBatchUs = std::max(m_diagMaxReadBatchUs, diag_us);
    Busy(busy);
}"""

ORIGINAL_WORLD = """void LinkServer::OnWorldTick() {
    QElapsedTimer busy;
    busy.start();
    Apply(m_world.Tick(QDateTime::currentMSecsSinceEpoch()));
    // The Rpc tunnels' resends and keepalives.
    for (auto& [id, end] : m_rpc)
        FlushRpc(*end);
    Busy(busy);
}"""

MEASURED_WORLD = """void LinkServer::OnWorldTick() {
    // The original periodic world timer is 50 ms. Record its actual dispatch
    // gap so Qt main-loop starvation is not confused with Coop retransmits.
    const qint64 diag_now = m_clock.nsecsElapsed();
    if (m_diagLastWorldTickNs != 0) {
        const quint64 gap_us = static_cast<quint64>((diag_now - m_diagLastWorldTickNs) / 1000);
        m_diagMaxWorldGapUs = std::max(m_diagMaxWorldGapUs, gap_us);
        if (gap_us > 75000)
            ++m_diagLateWorldTicks;
    }
    m_diagLastWorldTickNs = diag_now;
    QElapsedTimer busy;
    busy.start();
    Apply(m_world.Tick(QDateTime::currentMSecsSinceEpoch()));
    // The Rpc tunnels' resends and keepalives.
    for (auto& [id, end] : m_rpc)
        FlushRpc(*end);
    const quint64 world_us = static_cast<quint64>(busy.nsecsElapsed() / 1000);
    ++m_diagWorldTicks;
    m_diagWorldBusyUs += world_us;
    m_diagMaxWorldBusyUs = std::max(m_diagMaxWorldBusyUs, world_us);
    if (diag_now - m_diagWindowSinceNs >= 5'000'000'000LL) {
        qInfo().nospace().noquote()
            << "YT130_EVENTLOOP read_batches=" << m_diagReadBatches
            << " read_datagrams=" << m_diagReadDatagrams
            << " read_busy_us=" << m_diagReadBusyUs
            << " max_read_batch_us=" << m_diagMaxReadBatchUs
            << " max_read_batch_datagrams=" << m_diagMaxReadBatchDatagrams
            << " world_ticks=" << m_diagWorldTicks
            << " world_busy_us=" << m_diagWorldBusyUs
            << " max_world_busy_us=" << m_diagMaxWorldBusyUs
            << " max_world_gap_us=" << m_diagMaxWorldGapUs
            << " late_world_ticks=" << m_diagLateWorldTicks;
        m_diagWindowSinceNs = diag_now;
        m_diagReadBatches = m_diagReadDatagrams = m_diagReadBusyUs = 0;
        m_diagMaxReadBatchUs = m_diagMaxReadBatchDatagrams = 0;
        m_diagWorldTicks = m_diagWorldBusyUs = m_diagMaxWorldBusyUs = 0;
        m_diagMaxWorldGapUs = m_diagLateWorldTicks = 0;
    }
    Busy(busy);
}"""

# Earlier PR24 instruments this EXACT original read call to count UDP wire kind.
# Keep the existing RecordWire() functionality, rather than replacing it or
# requiring an impossible unmodified callback after the source staging chain.
WIRE_READ = "        m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);"
WIRE_MEASURE = """        const qint64 received = m_socket->readDatagram(
            raw.data(), raw.size(), &sender, &senderPort);
        if (received > 0)
            RecordWire(raw, true);"""
assert ORIGINAL_READ.count(WIRE_READ) == 1 and MEASURED_READ.count(WIRE_READ) == 1
ORIGINAL_READ = ORIGINAL_READ.replace(WIRE_READ, WIRE_MEASURE)
MEASURED_READ = MEASURED_READ.replace(WIRE_READ, WIRE_MEASURE)

HEADER_ANCHOR = """    QElapsedTimer m_clock;
    Database m_db;"""
HEADER_NEW = """    QElapsedTimer m_clock;
    // Diagnostics only. All callbacks run on the original single Qt link
    // event loop; no atomic operations or extra high-frequency logging.
    qint64 m_diagWindowSinceNs = 0;
    qint64 m_diagLastWorldTickNs = 0;
    quint64 m_diagReadBatches = 0;
    quint64 m_diagReadDatagrams = 0;
    quint64 m_diagReadBusyUs = 0;
    quint64 m_diagMaxReadBatchUs = 0;
    quint64 m_diagMaxReadBatchDatagrams = 0;
    quint64 m_diagWorldTicks = 0;
    quint64 m_diagWorldBusyUs = 0;
    quint64 m_diagMaxWorldBusyUs = 0;
    quint64 m_diagMaxWorldGapUs = 0;
    quint64 m_diagLateWorldTicks = 0;
    Database m_db;"""


def rewrite(cpp: str, header: str) -> tuple[str, str]:
    for key, old in (("read callback", ORIGINAL_READ),
                     ("50ms world callback", ORIGINAL_WORLD)):
        if cpp.count(old) != 1:
            raise ValueError("Pinned source drift in " + key)
    if header.count(HEADER_ANCHOR) != 1:
        raise ValueError("Pinned Qt header source changed")
    if "YT130_EVENTLOOP" in cpp or "m_diagReadBatches" in header:
        raise ValueError("Event loop instrumentation already staged")
    return (
        cpp.replace(ORIGINAL_READ, MEASURED_READ).replace(ORIGINAL_WORLD, MEASURED_WORLD),
        header.replace(HEADER_ANCHOR, HEADER_NEW),
    )


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Different official YT1.3 server version")
    for path, blob in ((CPP_FILE, CPP_BLOB), (HEADER_FILE, HEADER_BLOB)):
        if git(root, "rev-parse", "HEAD:" + path) != blob:
            raise ValueError("Wrong original blob: " + path)
    cpp = root / CPP_FILE
    h = root / HEADER_FILE
    cpp_out, header_out = rewrite(cpp.read_text(encoding="utf-8"),
                                  h.read_text(encoding="utf-8"))
    cpp.write_bytes(cpp_out.encode("utf-8"))
    h.write_bytes(header_out.encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_EVENTLOOP_READ_READY_VS_WORLD_TICK_INSTRUMENTED_NO_NETWORK_CHANGES")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_official_YT130_checkout", type=Path)
    apply(p.parse_args().disposable_official_YT130_checkout)
