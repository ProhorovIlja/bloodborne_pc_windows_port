#!/usr/bin/env python3
"""V130 CI-only Qt UDP SEND-call observability (not throughput optimization).

Baselines fail 64 peers at 114ms+ relay p99. Earlier V125 read fairness and
V128 lobby batching didn't fix it. Instrument BOTH source-verified native Qt
send loops to attribute kernel write errors, send syscall busy time, max
Qt write queue bytes, and whether traffic came from Hub or Co-op World.
No addresses, packet contents, identities, keys, gameplay policy, P2P or wire
formats logged. Diagnostics add timing overhead; NEVER treat as a perf fix.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import argparse
import stage_wire_traffic as wire

PIN=wire.PIN
CPP_FILE="server/src/link_server.cpp"
HEADER_FILE="server/src/link_server.h"
CPP_BLOB=wire.BLOBS[CPP_FILE]
HEADER_BLOB=wire.BLOBS[HEADER_FILE]
HUB_OLD="""    for (const auto& send : result.sends) {
        if (m_socket->writeDatagram(
                send.datagram, QHostAddress(send.to.ipv4), send.to.port) > 0)
            RecordWire(send.datagram, false);
    }"""
HUB_NEW="""    for (const auto& send : result.sends)
        SendMeasured(send.datagram, send.to.ipv4, send.to.port, false);"""
WORLD_OLD="""    for (const auto& send : result.sends) {
        if (const auto sealed = m_link.Seal(send.to, ServerLink::EncodeCoop(send.body))) {
            if (m_socket->writeDatagram(
                    *sealed, QHostAddress(send.to.ipv4), send.to.port) > 0)
                RecordWire(*sealed, false);
        }
    }"""
WORLD_NEW="""    for (const auto& send : result.sends) {
        if (const auto sealed = m_link.Seal(send.to, ServerLink::EncodeCoop(send.body)))
            SendMeasured(*sealed, send.to.ipv4, send.to.port, true);
    }"""
CPP_ANCHOR="void LinkServer::ReportWire() {"
CPP_NEW="""// V130 diagnostic only: records aggregate 5s output syscall latencies and
// errors, no payloads, endpoints, users, keys, or gameplay decisions.
qint64 LinkServer::SendMeasured(const QByteArray& datagram, quint32 ipv4,
                                quint16 port, bool world) {
    QElapsedTimer clock;
    clock.start();
    const qint64 sent = m_socket->writeDatagram(datagram, QHostAddress(ipv4), port);
    const quint64 elapsed_us = static_cast<quint64>(clock.nsecsElapsed() / 1000);
    ++m_diagSendCalls;
    m_diagSendBusyUs += elapsed_us;
    m_diagSendMaxUs = std::max(m_diagSendMaxUs, elapsed_us);
    if (world)
        ++m_diagWorldSendCalls;
    else
        ++m_diagHubSendCalls;
    if (sent < 0)
        ++m_diagSendErrors;
    else if (sent > 0)
        RecordWire(datagram, false);
    m_diagMaxPendingWriteBytes = std::max(
        m_diagMaxPendingWriteBytes,
        static_cast<quint64>(std::max<qint64>(m_socket->bytesToWrite(), 0)));
    return sent;
}

void LinkServer::ReportWire() {"""
LOG_OLD="""    m_wireOutPackets.fill(0);
    m_wireOutBytes.fill(0);
}"""
LOG_NEW="""    m_wireOutPackets.fill(0);
    m_wireOutBytes.fill(0);
    // Qt event-loop only, once per 5 seconds. Never log UDP destinations.
    qInfo().noquote().nospace()
        << "YT130_SEND_PROBE calls=" << m_diagSendCalls
        << " hub=" << m_diagHubSendCalls
        << " world=" << m_diagWorldSendCalls
        << " errors=" << m_diagSendErrors
        << " busy_us=" << m_diagSendBusyUs
        << " max_call_us=" << m_diagSendMaxUs
        << " max_pending_bytes=" << m_diagMaxPendingWriteBytes;
    m_diagSendCalls = m_diagHubSendCalls = m_diagWorldSendCalls = 0;
    m_diagSendErrors = m_diagSendBusyUs = m_diagSendMaxUs = 0;
    m_diagMaxPendingWriteBytes = 0;
}"""
H_ANCHOR="    void RecordWire(const QByteArray& datagram, bool incoming);"
H_NEW="""    void RecordWire(const QByteArray& datagram, bool incoming);
    qint64 SendMeasured(const QByteArray& datagram, quint32 ipv4,
                        quint16 port, bool world);"""
FIELD_ANCHOR="    qint64 m_wireLastAt = 0;"
FIELD_NEW="""    qint64 m_wireLastAt = 0;
    // V130 diagnostic counters; Qt event-loop owned. Never store addresses.
    quint64 m_diagSendCalls = 0;
    quint64 m_diagHubSendCalls = 0;
    quint64 m_diagWorldSendCalls = 0;
    quint64 m_diagSendErrors = 0;
    quint64 m_diagSendBusyUs = 0;
    quint64 m_diagSendMaxUs = 0;
    quint64 m_diagMaxPendingWriteBytes = 0;"""


def one(src: str, before: str, after: str, name: str) -> str:
    if src.count(before) != 1:
        raise ValueError("Source-pinned V130 Qt " + name + " changed, fail closed")
    return src.replace(before, after, 1)


def rewrite(cpp: str, header: str) -> tuple[str,str]:
    if "YT130_SEND_PROBE" in cpp or "m_diagSendErrors" in header:
        raise ValueError("V130 diagnostics already applied")
    cpp=one(cpp,HUB_OLD,HUB_NEW,"link/hub sends")
    cpp=one(cpp,WORLD_OLD,WORLD_NEW,"world/coop sends")
    cpp=one(cpp,CPP_ANCHOR,CPP_NEW,"native world send diagnostics")
    cpp=one(cpp,LOG_OLD,LOG_NEW,"5sec aggregate log/reset")
    header=one(header,H_ANCHOR,H_NEW,"declaration")
    header=one(header,FIELD_ANCHOR,FIELD_NEW,"single Qt event-loop counter state")
    if cpp.count("SendMeasured(*sealed,")!=1 or cpp.count("SendMeasured(send.datagram,")!=1:
        raise ValueError("Unexpected send replacement count")
    if cpp.count("m_socket->writeDatagram(datagram, QHostAddress(ipv4), port)")!=1:
        raise ValueError("Expected one shared measured output syscall")
    return cpp,header


def git(root: Path,*args: str) -> str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def apply(root: Path) -> None:
    root=root.resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=PIN:
        raise ValueError("Wrong pinned original YT 1.3 Qt source revision")
    for file,expected in ((CPP_FILE,CPP_BLOB),(HEADER_FILE,HEADER_BLOB)):
        if git(root,"rev-parse","HEAD:"+file)!=expected:
            raise ValueError("Pinned Qt original source blob changed "+file)
    cpp_file,header_file=root/CPP_FILE,root/HEADER_FILE
    cpp,header=rewrite(cpp_file.read_text(encoding="utf-8"),header_file.read_text(encoding="utf-8"))
    cpp_file.write_bytes(cpp.encode("utf-8"))
    header_file.write_bytes(header.encode("utf-8"))
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("YT130_V130_ORIGINAL_NATIVE_QT_UDP_SEND_CALL_DIAGNOSTICS_STAGED_NO_PERFORMANCE_CLAIM")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("disposable_pinned_yt130_checkout",type=Path)
    apply(p.parse_args().disposable_pinned_yt130_checkout)
