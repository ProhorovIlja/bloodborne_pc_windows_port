#!/usr/bin/env python3
"""V94 pin-sensitive backport of upstream Yharnam Together PR #365.

https://github.com/lKaniel/bloodborne-server/pull/365
Original pinned 77e3507 shadNet StreamExtractor accepts a 32-bit blob size
over INT_MAX through a signed-cast check; malicious pre-auth TCP input can
trigger an out-of-bounds read. Carry upstream's minimal repair, unchanged
semantics for well-formed small packets, no live server deployment.
"""
from __future__ import annotations

SERVER="server/src/stream_extractor.h"
MARKER="A size past INT_MAX made m_pos + (int)size negative"

def one(s,a,b,label):
    n=s.count(a)
    if n!=1: raise ValueError(f"V94 {label}: pinned source drift expected one anchor got {n}")
    return s.replace(a,b,1)

def patch_header(src):
    if MARKER in src:
        raise ValueError("V94 upstream bounds fix already present")
    src=one(src,
        '''    QByteArray getBytes(int n) {
        if (m_pos + n > m_data.size()) {''',
        '''    QByteArray getBytes(int n) {
        if (n < 0 || n > Remaining()) {''',
        "getBytes signed overflow and negative sizes")
    src=one(src,
        '''    QByteArray peekBytes(int n) const {
        if (m_pos + n > m_data.size())''',
        '''    QByteArray peekBytes(int n) const {
        if (n < 0 || n > Remaining())''',
        "peekBytes signed overflow and negative sizes")
    src=one(src,
        '''        if (m_pos + (int)size > m_data.size()) {
            m_error = true;
            return {};
        }
        QByteArray out(m_data.constData() + m_pos, size);''',
        '''        // A size past INT_MAX made m_pos + (int)size negative: a read of up to 4 GB past the
        // packet (any client, before signing in).
        if (size > static_cast<uint32_t>(Remaining())) {
            m_error = true;
            return {};
        }
        QByteArray out(m_data.constData() + m_pos, size);''',
        "getRawData pre-auth u32->int overflow")
    src=one(src,
        '''private:
    template <typename T>
    static T fromLe(T v) {''',
        '''private:
    qsizetype Remaining() const {
        return m_data.size() - m_pos;
    }

    template <typename T>
    static T fromLe(T v) {''',
        "remaining size helper")
    return src
