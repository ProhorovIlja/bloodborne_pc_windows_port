#!/usr/bin/env python3
"""Source-exact EXPERIMENT: bound Qt UDP reads per event-loop turn.

Never deploy directly, never touch production. A short continuation keeps
QUdpSocket draining even where Qt will not re-emit readyRead for unread packets.
Preserves every packet's normal Receive/Apply/auth/route path and signatures.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
EXPECTED_BLOBS = {
    "server/src/link_server.cpp": "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8",
    "server/src/link_server.h": "4530df9be35e161cd4e4fd56fe1f1696bb8b407b",
}

OLD_METHOD = """void LinkServer::OnReadyRead() {
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

NEW_METHOD = """void LinkServer::OnReadyRead() {
    // Experiment: under sustained UDP traffic do not monopolize the same Qt
    // event loop that runs the lobby/world timers and authorization callbacks.
    // Retain the original full auth, route, encryption and packet handling.
    constexpr int MaxDatagramsPerTurn = 64;
    constexpr qint64 MaxTurnBusyNs = 2'000'000; // 2 ms
    QElapsedTimer busy;
    busy.start();
    int handled = 0;
    while (m_socket->hasPendingDatagrams() && handled < MaxDatagramsPerTurn) {
        QByteArray raw;
        raw.resize(static_cast<int>(m_socket->pendingDatagramSize()));
        QHostAddress sender;
        uint16_t senderPort = 0;
        m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);
        ++handled;

        if (!raw.isEmpty() && ServerLink::KindOf(raw))
            HandleLink(raw, sender, senderPort);
        if (busy.nsecsElapsed() >= MaxTurnBusyNs)
            break;
    }
    Busy(busy);
    // Qt may not re-emit readyRead for packets that were not fully drained.
    // A guarded queued continuation prevents starvation AND duplicate queues;
    // it is tied to this QObject so it cannot run after the socket is gone.
    if (m_socket->hasPendingDatagrams() && !m_udpDrainQueued) {
        m_udpDrainQueued = true;
        QTimer::singleShot(0, this, [this] {
            m_udpDrainQueued = false;
            OnReadyRead();
        });
    }
}"""

OLD_MEMBER = "    QUdpSocket* m_socket;\n"
NEW_MEMBER = ("    QUdpSocket* m_socket;\n"
              "    // At most one zero-delay continuation for a partially drained UDP batch.\n"
              "    bool m_udpDrainQueued = false;\n")


def patch_text(cpp: str, header: str) -> tuple[str, str]:
    # The separate v1.3 auth staging may edit unrelated regions of these files.
    # Never rewrite a changed OnReadyRead implementation or ambiguous source.
    if cpp.count(OLD_METHOD) != 1 or header.count(OLD_MEMBER) != 1:
        raise ValueError("Unexpected current YT1.3 link-server source; no edits")
    if "m_udpDrainQueued" in cpp or "m_udpDrainQueued" in header:
        raise ValueError("Already modified; refuse duplicate UDP patch")
    changed_cpp = cpp.replace(OLD_METHOD, NEW_METHOD)
    changed_header = header.replace(OLD_MEMBER, NEW_MEMBER)
    return changed_cpp, changed_header


def git_read(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git_read(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong source revision; no writes")
    for relative, blob in EXPECTED_BLOBS.items():
        if git_read(root, "rev-parse", "HEAD:" + relative) != blob:
            raise ValueError("Unexpected upstream blob " + relative + "; no writes")
    cpp_file = root / "server/src/link_server.cpp"
    header_file = root / "server/src/link_server.h"
    if not cpp_file.is_file() or not header_file.is_file():
        raise ValueError("Missing staged source; no writes")
    before_cpp = cpp_file.read_text(encoding="utf-8")
    before_header = header_file.read_text(encoding="utf-8")
    changed_cpp, changed_header = patch_text(before_cpp, before_header)
    # Check first, commit both changes only after all verification succeeds.
    cpp_file.write_text(changed_cpp, encoding="utf-8")
    header_file.write_text(changed_header, encoding="utf-8")
    print("YT130_UDP_FAIR_READ_EXPERIMENT_STAGED_ONLY_NOT_PRODUCTION")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_upstream_checkout", type=Path)
    apply(parser.parse_args().disposable_upstream_checkout)
