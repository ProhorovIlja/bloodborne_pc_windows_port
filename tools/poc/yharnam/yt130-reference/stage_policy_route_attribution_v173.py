#!/usr/bin/env python3
"""V173: source-pinned ORIGINAL YT1.3 Qt server intentional channel filter census.

A generator's 'packets sent minus packets received' is NOT necessarily UDP loss:
RoutesNativePacket filters expected, unauthorized/unneeded game channels.
Count actual decisions at Hub::Routed() on every directed game entry, not an
inferred channel policy, and publish only aggregate counts once per 5-second
existing V155 wire window. No names, tokens, IPs, save, payload or identity.
NEVER changes routing, permissions, guest/game protocol, launcher or Fornex.
"""
from pathlib import Path
import subprocess
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOBS={
 "server/src/server_link.h":"eb23eeb2931ea288222b011be18e5c4915c4f802",
 "server/src/server_link.cpp":"eca0980de1e72177c38e1a0e3e613e9a97f13442",
 "server/src/link_server.cpp":"b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8",
}
MARKER="SHYT_V173_ORIGINAL_QT_POLICY_FILTER_ATTRIBUTION"
HEADER_OLD="    explicit Hub(qint64 quiet_ms = 3000, qint64 gone_ms = 60000, qint64 stats_ms = 10000,"
HEADER_NEW='''    // SHYT_V173_ORIGINAL_QT_POLICY_FILTER_ATTRIBUTION: additive count-only
    // diagnostics. Refused is an intentional authoritative gameplay decision,
    // NOT a network packet-loss observation. No account or endpoint keys.
    struct RouteAudit {
        quint64 allowed_entries = 0;
        quint64 filtered_entries = 0;
        quint64 filtered_enemy_hp_05 = 0;
        quint64 filtered_event_sync_31 = 0;
    };
    RouteAudit TakeRouteAudit() {
        const RouteAudit previous = m_routeAudit;
        m_routeAudit = {};
        return previous;
    }
'''+HEADER_OLD
FIELD_OLD="    quint64 dropped = 0;\n"
FIELD_NEW=FIELD_OLD+"    RouteAudit m_routeAudit{}; // V173 only; fixed four counters, no allocations\n"
ROUTED_OLD='''        if (packet_routes(sender.endpoint, target.endpoint, channel)) {
            return true;
        }
        ++sender.refused[channel];
        return false;'''
ROUTED_NEW='''        if (packet_routes(sender.endpoint, target.endpoint, channel)) {
            ++m_routeAudit.allowed_entries;
            return true;
        }
        ++m_routeAudit.filtered_entries;
        if (channel == 0x05)
            ++m_routeAudit.filtered_enemy_hp_05;
        if (channel == 0x31)
            ++m_routeAudit.filtered_event_sync_31;
        ++sender.refused[channel];
        return false;'''
WIRE_OLD='''    m_wireLastAt = now;
    for (size_t kind = 0; kind < m_wireInPackets.size(); ++kind) {'''
WIRE_NEW='''    m_wireLastAt = now;
    // SHYT_V173_ORIGINAL_QT_POLICY_FILTER_ATTRIBUTION:
    // The original Hub already classified the actual sender, recipient,
    // map, and authoritative enemy owner. These counters are a separate
    // stage BEFORE UDP socket submission, so 'refused' never means loss.
    const auto policy = m_link.TakeRouteAudit();
    if (policy.allowed_entries || policy.filtered_entries)
        qInfo().noquote().nospace()
            << "YT130_ROUTE_POLICY allowed_entries=" << policy.allowed_entries
            << " filtered_entries=" << policy.filtered_entries
            << " filtered_enemy_hp_05=" << policy.filtered_enemy_hp_05
            << " filtered_event_sync_31=" << policy.filtered_event_sync_31;
    for (size_t kind = 0; kind < m_wireInPackets.size(); ++kind) {'''

def one(s,old,new,label):
    if s.count(old)!=1 or new in s:
        raise ValueError("V173 exact original game route census drift: "+label)
    return s.replace(old,new,1)

def patch(h,hub,link):
    if MARKER in h or "YT130_ROUTE_POLICY" in link:
        raise ValueError("V173 already staged")
    if "YT130_WIRE_TRAFFIC" not in link or "void LinkServer::ReportWire()" not in link:
        raise ValueError("V173 requires verified existing V155 source wire staging")
    # No duplicate policy callback or modified gameplay decisions: only
    # numbers on the existing routed callback and existing 5-second log.
    h=one(h,HEADER_OLD,HEADER_NEW,"Hub public original route audit")
    h=one(h,FIELD_OLD,FIELD_NEW,"fixed-size route decision state")
    hub=one(hub,ROUTED_OLD,ROUTED_NEW,"existing route decision and refusal")
    link=one(link,WIRE_OLD,WIRE_NEW,"already instrumented Qt wire interval")
    return h,hub,link

def stage(base):
    base=Path(base).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(base),*args],text=True).strip()
    if git("rev-parse","HEAD")!=PIN:
        raise ValueError("V173 only original pinned YT1.3 disposable source")
    for path,expected in BLOBS.items():
        if git("rev-parse","HEAD:"+path)!=expected:
            raise ValueError("V173 original Git blob changed: "+path)
        if not (base/path).is_file() or (base/path).is_symlink():
            raise ValueError("V173 unsafe or missing original Qt file: "+path)
    h,hub,link=(base/path for path in BLOBS)
    a,b,c=patch(h.read_text(encoding="utf-8"),
                hub.read_text(encoding="utf-8"),
                link.read_text(encoding="utf-8"))
    # All three complete outputs are checked BEFORE writing any of them.
    h.write_text(a,encoding="utf-8")
    hub.write_text(b,encoding="utf-8")
    link.write_text(c,encoding="utf-8")
    subprocess.run(["git","-C",str(base),"diff","--check"],check=True)
    print("SHYT_V173_ORIGINAL_QT_POLICY_FILTER_COUNT_ONLY_STAGED_NOT_LOSS_PROOF")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: stage_policy_route_attribution_v173.py DISPOSABLE_PINNED_YT130")
    stage(sys.argv[1])
