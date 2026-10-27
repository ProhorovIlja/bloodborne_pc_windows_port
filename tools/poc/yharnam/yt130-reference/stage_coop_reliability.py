#!/usr/bin/env python3
"""EXPERIMENT ONLY: measure CoopStream fresh/resent/ack frames on native Qt server.

Official YT v1.3.0 source-pinned. Operates after the independently verified
lobby dedupe and wire-kind observational patches in a disposable checkout.
No changes to network encoding, crypto, authentication, route, packet priority,
timeouts, player identities, worlds or saved files.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOBS = {
    "server/src/bloodborne_world.cpp": "eca8c30d6fb78099b0f64a52388fd7d65f926e19",
    "server/src/bloodborne_world.h": "dfdbd49a30427b71c95e520dbc77498b521bce93",
}

CPP_PATCHES = (
    (
        '#include <QDateTime>\n',
        '#include <QDateTime>\n#include <QDebug>\n',
    ),
    (
        """void Service::SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms) {
    member.stream.Send(EncodeEnvelope(envelope), now_ms);""",
        """void Service::SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms) {
    // Diagnostic: one count per original reliable *message*, before chunking.
    ++m_diagEnvelopes[static_cast<int>(envelope.body_case())];
    member.stream.Send(EncodeEnvelope(envelope), now_ms);""",
    ),
    (
        """void Service::FlushSome(qint64 now_ms, Result& result) {""",
        """void Service::CountDiagnosticFrame(const std::vector<u8>& body) {
    // In the ORIGINAL 1.3 stream encoding; this read-only decoding runs on
    // disposable CI binaries only and makes no routing or payload decisions.
    ++m_diagFrames;
    m_diagBodyBytes += body.size();
    if (const auto frame = DecodeGameFrame(body)) {
        m_diagEntries += frame->entries.size();
        if (frame->entries.empty())
            ++m_diagAckOnly;
    }
}

void Service::ReportDiagnostics(qint64 now_ms) {
    if (m_diagAt == 0) {
        m_diagAt = now_ms;
        return;
    }
    if (now_ms - m_diagAt < 5000)
        return;
    quint64 pending_chunks = 0;
    quint64 pending_bytes = 0;
    quint64 blocked_members = 0;
    for (const auto& [key, member] : members) {
        pending_chunks += member.stream.Unacked();
        pending_bytes += member.stream.UnackedBytes();
        blocked_members += member.stream.Unacked() > 0 ? 1u : 0u;
    }
    const quint64 fresh = m_diagEntries >= m_diagResends
                              ? m_diagEntries - m_diagResends : 0;
    qInfo().noquote().nospace()
        << "YT130_COOP_RELIABILITY frames=" << m_diagFrames
        << " body_bytes=" << m_diagBodyBytes
        << " reliable_entries=" << m_diagEntries
        << " fresh_entries=" << fresh
        << " resent_entries=" << m_diagResends
        << " ack_only_frames=" << m_diagAckOnly
        << " pending_chunks=" << pending_chunks
        << " pending_bytes=" << pending_bytes
        << " blocked_members=" << blocked_members
        << " active_members=" << members.size();
    for (const auto& [body_case, count] : m_diagEnvelopes) {
        // Type IDs only; NO usernames, addresses, packet bodies, or secrets.
        qInfo().noquote().nospace()
            << "YT130_COOP_ORIGIN kind=" << body_case << " sends=" << count;
    }
    m_diagAt = now_ms;
    m_diagFrames = m_diagBodyBytes = m_diagEntries = 0;
    m_diagResends = m_diagAckOnly = 0;
    m_diagEnvelopes.clear();
}

void Service::FlushSome(qint64 now_ms, Result& result) {""",
    ),
    (
        """        member->to_flush = false;
        for (const std::vector<u8>& body : member->stream.Flush(now_ms)) {
            result.sends.append(""",
        """        member->to_flush = false;
        const quint64 before_resends = member->stream.Resends();
        for (const std::vector<u8>& body : member->stream.Flush(now_ms)) {
            CountDiagnosticFrame(body);
            result.sends.append(""",
    ),
    (
        """        if (member->stream.UnackedBytes() > limits.unacked_bytes) {
            over.push_back(member->key);
        }""",
        """        m_diagResends += member->stream.Resends() - before_resends;
        if (member->stream.UnackedBytes() > limits.unacked_bytes) {
            over.push_back(member->key);
        }""",
    ),
    (
        """    for (auto& [key, member] : members) {
        for (const std::vector<u8>& body : member.stream.Flush(now_ms)) {
            result.sends.append(""",
        """    for (auto& [key, member] : members) {
        const quint64 before_resends = member.stream.Resends();
        for (const std::vector<u8>& body : member.stream.Flush(now_ms)) {
            CountDiagnosticFrame(body);
            result.sends.append(""",
    ),
    (
        """        if (member.stream.UnackedBytes() > limits.unacked_bytes) {
            over.push_back(key);
        }""",
        """        m_diagResends += member.stream.Resends() - before_resends;
        if (member.stream.UnackedBytes() > limits.unacked_bytes) {
            over.push_back(key);
        }""",
    ),
    (
        """    Flush(now_ms, result);
    if (writer) {
        result.log.append(writer->TakeLog());
    }
    return result;
}

std::string Service::CharacterOf(""",
        """    Flush(now_ms, result);
    ReportDiagnostics(now_ms);
    if (writer) {
        result.log.append(writer->TakeLog());
    }
    return result;
}

std::string Service::CharacterOf(""",
    ),
)

H_PATCHES = (
    (
        """    void Flush(qint64 now_ms, Result& result);
    // Only the members sent something""",
        """    void Flush(qint64 now_ms, Result& result);
    // Disposable measurement only: no wire format, state, logic, identity changes.
    void CountDiagnosticFrame(const std::vector<u8>& body);
    void ReportDiagnostics(qint64 now_ms);
    // Only the members sent something""",
    ),
    (
        """    qint64 clock_ms = 0;   // the last time a call said (for the calls that say none)
};""",
        """    qint64 clock_ms = 0;   // the last time a call said (for the calls that say none)
    // Synthetic CI-only reliable co-op instrumentation, per server instance.
    qint64 m_diagAt = 0;
    quint64 m_diagFrames = 0;
    quint64 m_diagBodyBytes = 0;
    quint64 m_diagEntries = 0;
    quint64 m_diagResends = 0;
    quint64 m_diagAckOnly = 0;
    std::map<int, quint64> m_diagEnvelopes;
};""",
    ),
)


def replace_exact(text: str, changes, source: str) -> str:
    for original, replacement in changes:
        if text.count(original) != 1:
            raise ValueError(f"Ambiguous/drifted {source} source; no writes: {original[:90]!r}")
        text = text.replace(original, replacement)
    return text


def patch_text(cpp: str, header: str) -> tuple[str, str]:
    if "YT130_COOP_RELIABILITY" in cpp or "m_diagBodyBytes" in header:
        raise ValueError("Coop diagnostics already present; no repeated patch")
    return replace_exact(cpp, CPP_PATCHES, "C++"), replace_exact(header, H_PATCHES, "header")


def git_at(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git_at(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong official YT1.3.0 source pin")
    for path, blob in BLOBS.items():
        if git_at(root, "rev-parse", "HEAD:" + path) != blob:
            raise ValueError("Unexpected original YT source blob: " + path)
    cpp_file = root / "server/src/bloodborne_world.cpp"
    h_file = root / "server/src/bloodborne_world.h"
    cpp, header = patch_text(cpp_file.read_text(), h_file.read_text())
    cpp_file.write_text(cpp, encoding="utf-8")
    h_file.write_text(header, encoding="utf-8")
    print("YT130_COOP_RELIABILITY_DIAGNOSTIC_STAGED_DISPOSABLE_ONLY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_upstream_checkout", type=Path)
    apply(parser.parse_args().disposable_upstream_checkout)
