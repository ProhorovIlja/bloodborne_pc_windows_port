#!/usr/bin/env python3
"""V26 opt-in admission rate budget for strict member-authenticated servers."""
from pathlib import Path
WORLD="server/src/bloodborne_world.cpp"
WORLD_H="server/src/bloodborne_world.h"
HEADER="server/src/sh_ingress_quota.hpp"
HERE=Path(__file__).resolve().parent
def one(s,old,new,label):
    n=s.count(old)
    if n != 1: raise ValueError(f"V26 {label}: expected 1 source anchor, got {n}")
    return s.replace(old,new,1)
def world_h(s):
    if "SH-INGRESS-QUOTA-V26" in s:raise ValueError("V26 already applied")
    s=one(s, '#include "bloodborne_party_boards.h"',
        '#include "bloodborne_party_boards.h"\n#include "sh_ingress_quota.hpp" // SH-INGRESS-QUOTA-V26',
        'header')
    s=one(s,'        bool enemy_owner = false;',
        '''        bool enemy_owner = false;
        // Per linked peer: bounded message/byte costs, not a global cap.
        SeamlessHunt::Ingress::Budget ingress;
        std::uint32_t rejected_over_budget = 0;
        qint64 last_budget_notice_ms = 0;''','member quota')
    return s
def world(s):
    if "SH-INGRESS-QUOTA-V26" in s:raise ValueError("V26 already applied")
    s=one(s,'#include "bloodborne_world.h"',
        '#include "bloodborne_world.h"\n#include "sh_ingress_quota.hpp" // SH-INGRESS-QUOTA-V26',
        'header')
    s=one(s,
        '''    for (const std::vector<u8>& message : messages) {
        if (const auto envelope = DecodeEnvelope(message)) {''',
        '''    for (const std::vector<u8>& message : messages) {
        // Opt-in strict rooms: stop parse floods before protobuf decoding.
        // Default/legacy PvE stays untouched. No background anti-cheat thread.
        if (SeamlessHunt::Identity::StrictMode() &&
            !member.ingress.Accept(message.size(), now_ms)) {
            if (member.rejected_over_budget < 0xffffffffu) ++member.rejected_over_budget;
            if (SeamlessHunt::SessionGuard::ShouldAudit(now_ms, member.last_budget_notice_ms)) {
                member.last_budget_notice_ms = now_ms;
                result.log.append(QStringLiteral("co-op %1: throttled malformed/flooding traffic (%2)")
                    .arg(QString::fromStdString(Who(member))).arg(member.rejected_over_budget));
            }
            continue;
        }
        if (const auto envelope = DecodeEnvelope(message)) {''',
        'pre-decode budget')
    return s
def transform(sources):
    return {WORLD:world(sources[WORLD]), WORLD_H:world_h(sources[WORLD_H]),
            HEADER:(HERE/'sh_ingress_quota.hpp').read_text('utf8')}
