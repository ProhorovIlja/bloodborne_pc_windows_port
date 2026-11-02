#!/usr/bin/env python3
"""Attribute native YT1.3 Coop(7) protobuf ENCODED payload bytes per type.

Source-pinned, read-only, CI-only. Does not log serialized content, names,
addresses, tokens, session keys or game packet bytes. Counts original
envelopes before reliable chunking and retry. Wire bytes remain separate.
"""
from pathlib import Path
import argparse
import subprocess
import stage_coop_reliability as previous

PIN = previous.PIN
CPP = "server/src/bloodborne_world.cpp"
HEADER = "server/src/bloodborne_world.h"
BLOBS = previous.BLOBS

OLD_SEND = """    ++m_diagEnvelopes[static_cast<int>(envelope.body_case())];
    member.stream.Send(EncodeEnvelope(envelope), now_ms);"""
NEW_SEND = """    const auto encoded = EncodeEnvelope(envelope);
    const int body_case = static_cast<int>(envelope.body_case());
    ++m_diagEnvelopes[body_case];
    m_diagEncodedBytes[body_case] += encoded.size();
    member.stream.Send(encoded, now_ms);"""
OLD_LOG = """            << "YT130_COOP_ORIGIN kind=" << body_case << " sends=" << count;"""
NEW_LOG = """            << "YT130_COOP_ORIGIN kind=" << body_case << " sends=" << count
            << " encoded_bytes=" << m_diagEncodedBytes[body_case];"""
OLD_CLEAR = """    m_diagEnvelopes.clear();"""
NEW_CLEAR = """    m_diagEnvelopes.clear();
    m_diagEncodedBytes.clear();"""
OLD_MAP = """    std::map<int, quint64> m_diagEnvelopes;"""
NEW_MAP = """    std::map<int, quint64> m_diagEnvelopes;
    // Before chunking/retransmits: source message bytes, not NIC bytes.
    std::map<int, quint64> m_diagEncodedBytes;"""

def once(s, old, new, label):
    if s.count(old) != 1:
        raise ValueError("Original reliable envelope source drift at " + label)
    return s.replace(old, new)

def rewrite(cpp, header):
    if "m_diagEncodedBytes" in cpp or "m_diagEncodedBytes" in header:
        raise ValueError("Previously staged")
    if "YT130_COOP_RELIABILITY" not in cpp or "CountDiagnosticFrame" not in cpp:
        raise ValueError("Original CoopStage must be applied first")
    cpp = once(cpp, OLD_SEND, NEW_SEND, "single encode and original Send")
    cpp = once(cpp, OLD_LOG, NEW_LOG, "source-only body_case log")
    cpp = once(cpp, OLD_CLEAR, NEW_CLEAR, "interval reset")
    header = once(header, OLD_MAP, NEW_MAP, "bounded counter map")
    return cpp, header

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def apply(root):
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Only original official YT1.3 checkout")
    files = [root / CPP, root / HEADER]
    for name, file in zip((CPP, HEADER), files):
        if git(root, "rev-parse", "HEAD:" + name) != BLOBS[name] or file.is_symlink():
            raise ValueError("Wrong original source SHA or symlink " + name)
        if not git(root, "diff", "--", name):
            raise ValueError("Original CoopStage missing " + name)
    a, b = rewrite(*(p.read_text(encoding="utf-8") for p in files))
    files[0].write_text(a, encoding="utf-8")
    files[1].write_text(b, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_COOP7_ORIGIN_COUNTS_AND_ENCODED_BYTES_SOURCE_INSTRUMENTED")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_original_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_original_yt130_checkout)
