#!/usr/bin/env python3
"""V22 pinned-server source transform: cheap ingress validation, no auto-bans."""
from pathlib import Path
BOARDS="server/src/bloodborne_party_boards.cpp"
WORLD="server/src/bloodborne_world.cpp"
WORLD_H="server/src/bloodborne_world.h"
GUARD="server/src/sh_session_guard.hpp"
HERE=Path(__file__).resolve().parent

def one(s,old,new,name):
    if s.count(old)!=1:raise ValueError(f"V22 {name}: pinned source drift (found {s.count(old)})")
    return s.replace(old,new,1)

def boards(s):
    if "SH-SERVER-TRUST-V22" in s: raise ValueError("V22 already applied to boards")
    s=one(s,'#include <algorithm>', '#include <algorithm>\n#include "sh_session_guard.hpp" // SH-SERVER-TRUST-V22',"include")
    s=one(s,'        std::uint32_t damage = 0;',
          '        std::uint32_t damage = 0; // V22: saturated, bounded claims only',
          'initial total')
    s=one(s,'                    damage += hit.damage();',
          '                    damage = SeamlessHunt::SessionGuard::AddReviveDamage(damage, hit.damage());',
          'saturating revive total')
    return s

def world_h(s):
    if "SH-SERVER-TRUST-V22" in s: raise ValueError("V22 already applied to header")
    s=one(s,'        bool enemy_owner = false;',
          '''        bool enemy_owner = false;
        // SH-SERVER-TRUST-V22: per-link sparse audit. No periodic polling.
        qint64 last_invalid_vitals_log_ms = 0;
        std::uint32_t rejected_vitals = 0;''',"member diagnostics")
    return s

def world(s):
    if "SH-SERVER-TRUST-V22" in s: raise ValueError("V22 already applied to service")
    s=one(s,'#include "bloodborne_world.h"',
          '#include "bloodborne_world.h"\n#include <array>\n#include "sh_session_guard.hpp" // SH-SERVER-TRUST-V22',
          'include')
    needle='''    case bbcoop::Envelope::kVitals: {
        if (const bbcoop::Vitals& vitals = envelope.vitals();
            vitals.map() != 0 && (vitals.vital() == 1 || vitals.vital() == 2) &&
            vitals.has_at()) { // up or down where it stands'''
    repl='''    case bbcoop::Envelope::kVitals: {
        // Cheap server-side sanity check BEFORE trusting positions or updating
        // the party's health/revive board. Ordinary clients need no extra packets.
        const auto& report = envelope.vitals();
        namespace Guard = SeamlessHunt::SessionGuard;
        Guard::VitalsReport values{
            .vital = report.vital(), .hp = report.hp(), .max_hp = report.max(),
            .vials = report.vials(), .bullets = report.bullets(),
            .has_position = report.has_at(),
            .x = report.has_at() ? report.at().x() : 0.0f,
            .y = report.has_at() ? report.at().y() : 0.0f,
            .z = report.has_at() ? report.at().z() : 0.0f,
        };
        bool valid = Guard::SafeVitalValues(values) &&
                     report.hits_size() <= int(Guard::MaxReviveHitEntries);
        if (valid) {
            // Avoid dynamic allocation and protect the tiny hit table.
            std::array<Guard::ReviveHit, Guard::MaxReviveHitEntries> claims{};
            for (int i=0;i<report.hits_size();++i) {
                const auto& hit=report.hits(i);
                claims[std::size_t(i)] = {hit.target(), hit.down(), hit.damage()};
            }
            valid = Guard::SafeReviveHits(
                std::span<const Guard::ReviveHit>(claims.data(), std::size_t(report.hits_size())));
        }
        if (!valid) {
            ++member.rejected_vitals;
            if (Guard::ShouldAudit(now_ms, member.last_invalid_vitals_log_ms)) {
                member.last_invalid_vitals_log_ms = now_ms;
                result.log.append(QStringLiteral("co-op %1: refused malformed vitals (%2 rejected)")
                    .arg(QString::fromStdString(member.name))
                    .arg(member.rejected_vitals));
            }
            return;
        }
        if (const bbcoop::Vitals& vitals = envelope.vitals();
            vitals.map() != 0 && (vitals.vital() == 1 || vitals.vital() == 2) &&
            vitals.has_at()) { // up or down where it stands'''
    s=one(s,needle,repl,'vitals ingress')
    s=one(s,
       '''    const QByteArray party = QByteArray::fromStdString(hello.party()).trimmed();
    if (hello.protocol() != CoopProtocol) {''',
       '''    // V22: reject hostile identity metadata before creating a party key.
    const bool safe_ids =
        SeamlessHunt::SessionGuard::SafeWireText(hello.member(), 96) &&
        SeamlessHunt::SessionGuard::SafeWireText(hello.party(), 512);
    const QByteArray party = safe_ids ? QByteArray::fromStdString(hello.party()).trimmed()
                                    : QByteArray{};
    if (!safe_ids) {
        welcome.set_text("invalid member name or party key");
    } else if (hello.protocol() != CoopProtocol) {''',"hello bounds")
    s=one(s,
       '''    if (hello.protocol() != CoopProtocol || hello.member().empty()) {''',
       '''    if (hello.protocol() != CoopProtocol ||
        !SeamlessHunt::SessionGuard::SafeWireText(hello.member(), 96) ||
        !SeamlessHunt::SessionGuard::SafeWireText(hello.name(), 192)) {''',"lobby hello bounds")
    return s

def transform(src):
    return {BOARDS:boards(src[BOARDS]),WORLD:world(src[WORLD]),WORLD_H:world_h(src[WORLD_H]),
            GUARD:(HERE/"sh_session_guard.hpp").read_text('utf8')}
