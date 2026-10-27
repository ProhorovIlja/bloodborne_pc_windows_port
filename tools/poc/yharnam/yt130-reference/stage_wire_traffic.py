#!/usr/bin/env python3
"""Source-exact EXPERIMENTAL wire traffic attribution for disposable YT1.3 Qt server.

Counts datagram categories by the authenticated protocol's clear header kind
without logging addresses, payloads, usernames, passwords, tokens or keys.
Counts game relay (Kind 3), ping/pong, CoopStream (Kind 7) and RPC (Kind 8).
Only intercepts main LinkServer::OnReadyRead / Apply output paths. No protocol
semantics, routing decisions, encryption or game client code are changed.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOBS = {
    "server/src/link_server.cpp": "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8",
    "server/src/link_server.h": "4530df9be35e161cd4e4fd56fe1f1696bb8b407b",
}

PATCHES_CPP = (
    (
        "        m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);",
        """        const qint64 received = m_socket->readDatagram(
            raw.data(), raw.size(), &sender, &senderPort);
        if (received > 0)
            RecordWire(raw, true);""",
    ),
    (
        """    Apply(m_link.Tick(m_clock.elapsed()));
    Busy(busy);
}

void LinkServer::OnWorldTick() {""",
        """    Apply(m_link.Tick(m_clock.elapsed()));
    Busy(busy);
    ReportWire();
}

void LinkServer::RecordWire(const QByteArray& datagram, bool incoming) {
    // On-the-wire kind byte is available before decryption and is also on
    // authenticated game messages. Unknown kinds have their own bin (0).
    const int kind = datagram.size() > 8 && static_cast<quint8>(datagram[8]) <= 11
                         ? static_cast<quint8>(datagram[8]) : 0;
    auto& packets = incoming ? m_wireInPackets : m_wireOutPackets;
    auto& bytes = incoming ? m_wireInBytes : m_wireOutBytes;
    ++packets[static_cast<size_t>(kind)];
    bytes[static_cast<size_t>(kind)] += static_cast<quint64>(datagram.size());
}

void LinkServer::ReportWire() {
    const qint64 now = m_clock.elapsed();
    if (m_wireLastAt == 0) {
        m_wireLastAt = now;
        return;
    }
    if (now - m_wireLastAt < 5000)
        return;
    m_wireLastAt = now;
    for (size_t kind = 0; kind < m_wireInPackets.size(); ++kind) {
        if (!(m_wireInPackets[kind] || m_wireOutPackets[kind]))
            continue;
        qInfo().noquote().nospace()
            << "YT130_WIRE_TRAFFIC kind=" << kind
            << " in_packets=" << m_wireInPackets[kind]
            << " in_bytes=" << m_wireInBytes[kind]
            << " out_packets=" << m_wireOutPackets[kind]
            << " out_bytes=" << m_wireOutBytes[kind];
    }
    m_wireInPackets.fill(0);
    m_wireInBytes.fill(0);
    m_wireOutPackets.fill(0);
    m_wireOutBytes.fill(0);
}

void LinkServer::OnWorldTick() {""",
    ),
    (
        """    for (const auto& send : result.sends)
        m_socket->writeDatagram(send.datagram, QHostAddress(send.to.ipv4), send.to.port);
    for (const auto& line : result.log)""",
        """    for (const auto& send : result.sends) {
        if (m_socket->writeDatagram(
                send.datagram, QHostAddress(send.to.ipv4), send.to.port) > 0)
            RecordWire(send.datagram, false);
    }
    for (const auto& line : result.log)""",
    ),
    (
        """    for (const auto& send : result.sends)
        if (const auto sealed = m_link.Seal(send.to, ServerLink::EncodeCoop(send.body)))
            m_socket->writeDatagram(*sealed, QHostAddress(send.to.ipv4), send.to.port);
    for (const auto& line : result.log)""",
        """    for (const auto& send : result.sends) {
        if (const auto sealed = m_link.Seal(send.to, ServerLink::EncodeCoop(send.body))) {
            if (m_socket->writeDatagram(
                    *sealed, QHostAddress(send.to.ipv4), send.to.port) > 0)
                RecordWire(*sealed, false);
        }
    }
    for (const auto& line : result.log)""",
    ),
)
PATCHES_HEADER = (
    ("#include <map>\n", "#include <array>\n#include <map>\n"),
    (
        "    void HandleLink(const QByteArray& datagram, const QHostAddress& sender, uint16_t senderPort);",
        """    void HandleLink(const QByteArray& datagram, const QHostAddress& sender, uint16_t senderPort);
    // Experiment-only traffic counters: no payloads or identifiers logged.
    void RecordWire(const QByteArray& datagram, bool incoming);
    void ReportWire();""",
    ),
    (
        "    QUdpSocket* m_socket;\n",
        """    QUdpSocket* m_socket;
    // Kind 0 is unknown, 1..11 official LinkVersion=4 wire kinds.
    std::array<quint64, 12> m_wireInPackets{};
    std::array<quint64, 12> m_wireInBytes{};
    std::array<quint64, 12> m_wireOutPackets{};
    std::array<quint64, 12> m_wireOutBytes{};
    qint64 m_wireLastAt = 0;
""",
    ),
)


def patch_text(cpp: str, header: str) -> tuple[str, str]:
    # The auth staging may already edit unrelated methods in these two files.
    # Every mutation must match exactly ONE untouched upstream source fragment.
    if "YT130_WIRE_TRAFFIC" in cpp or "m_wireInPackets" in header:
        raise ValueError("Repeated instrumentation forbidden")
    for old, new in PATCHES_CPP:
        if cpp.count(old) != 1:
            raise ValueError("Missing or ambiguous C++ source fragment: " + old[:70])
        cpp = cpp.replace(old, new)
    for old, new in PATCHES_HEADER:
        if header.count(old) != 1:
            raise ValueError("Missing or ambiguous header fragment: " + old[:70])
        header = header.replace(old, new)
    return cpp, header


def git_at(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git_at(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Upstream revision differs from pinned official YT1.3")
    for filename, digest in BLOBS.items():
        if git_at(root, "rev-parse", "HEAD:" + filename) != digest:
            raise ValueError("Unexpected upstream source: " + filename)
    cpp_path = root / "server/src/link_server.cpp"
    header_path = root / "server/src/link_server.h"
    cpp, header = patch_text(
        cpp_path.read_text(encoding="utf-8"), header_path.read_text(encoding="utf-8")
    )
    cpp_path.write_text(cpp, encoding="utf-8")
    header_path.write_text(header, encoding="utf-8")
    print("YT130_WIRE_TRAFFIC_EXPERIMENT_STAGED_DISPOSABLE_ONLY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_upstream_checkout", type=Path)
    apply(parser.parse_args().disposable_upstream_checkout)
