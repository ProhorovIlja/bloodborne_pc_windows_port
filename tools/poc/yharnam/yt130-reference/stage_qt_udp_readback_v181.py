#!/usr/bin/env python3
"""V181: exact pinned YT1.3 LinkServer socket readback and UDP read safety.

Original game's actual Qt relay: report the effective (possibly kernel-capped)
socket options after bind, and ignore unsuccessful/truncated readDatagram.
No policy, protocol, game data, packet count, deployment or kernel sysctl changes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "server/src/link_server.cpp"
MARK = "SHYT_V181_QT_UDP_BUFFER_READBACK_AND_READ_GUARD"
BUFF_OLD = """    m_socket->setSocketOption(QAbstractSocket::ReceiveBufferSizeSocketOption, 16 << 20);
    m_socket->setSocketOption(QAbstractSocket::SendBufferSizeSocketOption, 16 << 20);
    qInfo().nospace().noquote() << "Link UDP listener on: " << addr.toString() << ":" << port;"""
BUFF_NEW = """    m_socket->setSocketOption(QAbstractSocket::ReceiveBufferSizeSocketOption, 16 << 20);
    m_socket->setSocketOption(QAbstractSocket::SendBufferSizeSocketOption, 16 << 20);
    // SHYT_V181_QT_UDP_BUFFER_READBACK_AND_READ_GUARD: socket options may
    // be capped by OS rmem_max/wmem_max. Report actual values only once on bind.
    // On Linux SO_RCVBUF readback may be doubled: do NOT treat it as
    // guaranteed room for that many bytes of payload or socket-specific loss.
    const int udp_recv_buf = m_socket->socketOption(
        QAbstractSocket::ReceiveBufferSizeSocketOption).toInt();
    const int udp_send_buf = m_socket->socketOption(
        QAbstractSocket::SendBufferSizeSocketOption).toInt();
    qInfo().nospace().noquote()
        << "Link UDP socket buffers requested_bytes=" << (16 << 20)
        << " effective_receive_bytes=" << udp_recv_buf
        << " effective_send_bytes=" << udp_send_buf;
    if (udp_recv_buf > 0 && udp_recv_buf < (16 << 20))
        qWarning() << "Link UDP receive buffer below requested size;"
                      " check the effective OS socket limit before 200-player tests";
    qInfo().nospace().noquote() << "Link UDP listener on: " << addr.toString() << ":" << port;"""
READ_OLD = """        m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);

        if (raw.isEmpty())
            continue;"""
READ_NEW = """        const qint64 bytes_read =
            m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);
        // V181: failure or short read must NEVER send untouched QByteArray
        // bytes into the authenticated link decoder. No payload/IDs logged.
        if (bytes_read <= 0 || bytes_read != raw.size())
            continue;"""


def replace_exact(source: str, old: str, new: str, purpose: str) -> str:
    if source.count(old) != 1 or new in source:
        raise ValueError("V181 original Qt source drift: " + purpose)
    return source.replace(old, new, 1)


def patch(source: str) -> str:
    if MARK in source:
        raise ValueError("V181 already applied")
    if ("void LinkServer::OnReadyRead()" not in source
            or "bool LinkServer::Start(" not in source):
        raise ValueError("V181 expected real Qt LinkServer methods")
    source = replace_exact(source, BUFF_OLD, BUFF_NEW, "post-bind socket readback")
    source = replace_exact(source, READ_OLD, READ_NEW, "actual UDP read result")
    return source


def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    source_file = root / FILE
    if (source_file.is_symlink() or not source_file.is_file()
            or subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL).strip() != PIN):
        raise ValueError("V181 requires disposable, exact pinned original Qt server")
    before = source_file.read_text(encoding="utf-8")
    after = patch(before)
    source_file.write_text(after, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_V181_NATIVE_QT_EFFECTIVE_UDP_BUFFERS_AND_READ_RESULT_GUARDED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pinned_original", type=Path)
    stage(parser.parse_args().pinned_original)
