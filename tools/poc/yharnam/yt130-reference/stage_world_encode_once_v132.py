#!/usr/bin/env python3
"""Source-exact YT1.3 game-server protobuf fan-out: encode once per broadcast.

V130 real Qt metrics: server 200 simulated peers, 265581 CoopStream datagrams,
22,785 reliable resends, 24,519 VitalsBoard and 14,846 LobbyState sends.
Original Service::SendTo serialized identical protobuf messages separately
for every recipient (SendBoards, SendEntries, SendOwners, SendToOthers).
This stages AFTER existing PR37 CoopStream diagnostics to retain per-recipient\nmessage counters. It avoids repeated encoding while preserving exact original
EncodeEnvelope bytes, per-recipient reliable CoopStream::Send, flush ordering,
authorization/world names, invader visibility and all 5-player rules.
No P2P, no packet drops, no reliability/class changes, no production install.

Do not extrapolate better QoS without native original bbload 4-200 tests.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
CPP="server/src/bloodborne_world.cpp"
HEADER="server/src/bloodborne_world.h"
BLOBS={
    CPP:"eca8c30d6fb78099b0f64a52388fd7d65f926e19",
    HEADER:"dfdbd49a30427b71c95e520dbc77498b521bce93",
}
SENDTO_OLD="""void Service::SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms) {
    // Diagnostic: one count per original reliable *message*, before chunking.
    ++m_diagEnvelopes[static_cast<int>(envelope.body_case())];
    member.stream.Send(EncodeEnvelope(envelope), now_ms);
    if (!member.to_flush) {
        member.to_flush = true;
        flush_now.push_back(&member);
    }
}"""
SENDTO_NEW="""// V132: the already encoded bytes may be shared by recipients because
// CoopStream::Send copies them into each recipient's own reliable chunks.
void Service::SendEncodedTo(Member& member, const bbcoop::Envelope& envelope,
                            std::span<const u8> encoded, qint64 now_ms) {
    // Preserve existing read-only per-recipient envelope telemetry.
    ++m_diagEnvelopes[static_cast<int>(envelope.body_case())];
    member.stream.Send(encoded, now_ms);
    if (!member.to_flush) {
        member.to_flush = true;
        flush_now.push_back(&member);
    }
}

void Service::SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms) {
    const auto encoded = EncodeEnvelope(envelope);
    SendEncodedTo(member, envelope, encoded, now_ms);
}"""
HEADER_SENDTO="    void SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms);"
HEADER_REPLACE="""    void SendEncodedTo(Member& member, const bbcoop::Envelope& envelope,
                       std::span<const u8> encoded,
                       qint64 now_ms);
    void SendTo(Member& member, const bbcoop::Envelope& envelope, qint64 now_ms);"""
HEADER_INCLUDE="#include <optional>\n"
HEADER_INCLUDE_NEW="#include <optional>\n#include <span>\n"
SEND_ENTRIES_OLD="""    *envelope.mutable_entries() = ToMessage(world.host.Epoch(), world.host.Last(), entries);
    for (auto& [key, member] : members) {
        if (member.party == world.name) {
            SendTo(member, envelope, now_ms);
        }
    }
    world.heartbeat_ms = now_ms;"""
SEND_ENTRIES_NEW="""    *envelope.mutable_entries() = ToMessage(world.host.Epoch(), world.host.Last(), entries);
    const auto encoded = EncodeEnvelope(envelope);
    for (auto& [key, member] : members) {
        if (member.party == world.name) {
            SendEncodedTo(member, envelope, encoded, now_ms);
        }
    }
    world.heartbeat_ms = now_ms;"""
SEND_OTHERS_OLD="""void Service::SendToOthers(PartyWorld& world, const Member& from, const bbcoop::Envelope& envelope,
                           qint64 now_ms) {
    for (auto& [key, member] : members) {
        if (member.party == world.name && &member != &from) {
            SendTo(member, envelope, now_ms);
        }
    }
}"""
SEND_OTHERS_NEW="""void Service::SendToOthers(PartyWorld& world, const Member& from, const bbcoop::Envelope& envelope,
                           qint64 now_ms) {
    const auto encoded = EncodeEnvelope(envelope);
    for (auto& [key, member] : members) {
        if (member.party == world.name && &member != &from) {
            SendEncodedTo(member, envelope, encoded, now_ms);
        }
    }
}"""
# Match only the cooperator fanout section. The V108 3-invader patch adds
# an important privacy-filtered hostile-only board AFTER this section.
# It must stay verbatim, not be replaced by a broadcast of cooperator HP.
BOARDS_OLD="""    for (const bbcoop::Envelope& board : boards) {
        if (only != nullptr) {
            SendTo(*only, board, now_ms);
            continue;
        }
        for (auto& [key, member] : members) {
            if (member.party == world.name) {
                SendTo(member, board, now_ms);
            }
        }"""
BOARDS_NEW="""    for (const bbcoop::Envelope& board : boards) {
        if (only != nullptr) {
            SendTo(*only, board, now_ms);
            continue;
        }
        const auto encoded = EncodeEnvelope(board);
        for (auto& [key, member] : members) {
            if (member.party == world.name) {
                SendEncodedTo(member, board, encoded, now_ms);
            }
        }"""
# V108 changes invader ownership fanout from one hostile to up to three.
# Patch the cooperator loop separately and its original hostile loop intact.
OWNERS_OLD="""    if (only != nullptr) {
        SendTo(*only, envelope, now_ms);
        return;
    }
    for (auto& [key, member] : members) {
        if (member.party == world.name) {
            SendTo(member, envelope, now_ms);
        }
    }"""
OWNERS_NEW="""    if (only != nullptr) {
        SendTo(*only, envelope, now_ms);
        return;
    }
    const auto encoded = EncodeEnvelope(envelope);
    for (auto& [key, member] : members) {
        if (member.party == world.name) {
            SendEncodedTo(member, envelope, encoded, now_ms);
        }
    }"""
HOSTILE_OWNERS_OLD="""    // SHYT-V108-MULTI-INVADER: every active hostile needs the owners for the map it visits.
    if (const auto bucket = invasions.find(world.name); bucket != invasions.end()) {
        for (const auto& [id, invasion] : bucket->second) {
            if (!invasion.joined) continue;
            if (const auto invader = members.find(invasion.invader);
                invader != members.end()) SendTo(invader->second, envelope, now_ms);
        }
    }"""
HOSTILE_OWNERS_NEW=HOSTILE_OWNERS_OLD.replace(
    "SendTo(invader->second, envelope, now_ms)",
    "SendEncodedTo(invader->second, envelope, encoded, now_ms)")
PATCHES=(
    ("SendTo preserved reliable flush",SENDTO_OLD,SENDTO_NEW),
    ("WorldLog Entries broadcast",SEND_ENTRIES_OLD,SEND_ENTRIES_NEW),
    ("ToOthers broadcast",SEND_OTHERS_OLD,SEND_OTHERS_NEW),
    ("World Boards broadcast",BOARDS_OLD,BOARDS_NEW),
    ("Enemy owners cooperator fanout",OWNERS_OLD,OWNERS_NEW),
    ("V108 three invader owner fanout",HOSTILE_OWNERS_OLD,HOSTILE_OWNERS_NEW),
)


def exact_replace(text:str,old:str,new:str,label:str)->str:
    if text.count(old)!=1:
        raise ValueError("Original pinned Qt World V132 source drift: "+label)
    return text.replace(old,new,1)


def rewrite(cpp:str,header:str)->tuple[str,str]:
    if "V132: the already encoded bytes" in cpp or "SendEncodedTo" in header:
        raise ValueError("World encoding optimization already applied")
    for label,old,new in PATCHES:
        cpp=exact_replace(cpp,old,new,label)
    header=exact_replace(header,HEADER_SENDTO,HEADER_REPLACE,"World API")
    header=exact_replace(header,HEADER_INCLUDE,HEADER_INCLUDE_NEW,"explicit span include")
    if cpp.count("void Service::SendEncodedTo(")!=1:
        raise ValueError("Missing single shared byte router")
    if cpp.count("member.stream.Send(encoded, now_ms);")!=1 or cpp.count("++m_diagEnvelopes[static_cast<int>(envelope.body_case())];")!=1:
        raise ValueError("Changed reliable stream per-recipient semantics")
    if "SHYT-V108-ALLIED-HOSTILE-VITALS" not in cpp or "SendTo(visitor->second, safe, now_ms)" not in cpp:
        raise ValueError("Lost privacy-filtered V108 hostile ONLY vitals")
    if "SendEncodedTo(invader->second, envelope, encoded, now_ms)" not in cpp:
        raise ValueError("Lost invader enemy-owner broadcast")
    if "SendTo(*only, board, now_ms);" not in cpp:
        raise ValueError("Lost individual board delivery")
    return cpp,header


def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def apply(root:Path)->None:
    root=root.resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=PIN:
        raise ValueError("Not pinned original YT1.3 source")
    for file,blob in BLOBS.items():
        if git(root,"rev-parse","HEAD:"+file)!=blob:
            raise ValueError("Original World source blob changed: "+file)
    cpp,h=root/CPP,root/HEADER
    if "SHYT-V108-ALLIED-HOSTILE-VITALS" not in cpp.read_text(encoding="utf-8"):
        raise ValueError("Apply V108 three-invader privacy staging BEFORE V132")
    cp,hd=rewrite(cpp.read_text(encoding="utf-8"),h.read_text(encoding="utf-8"))
    cpp.write_bytes(cp.encode("utf-8"))
    h.write_bytes(hd.encode("utf-8"))
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("YT130_V132_WORLD_FANOUT_SINGLE_ENCODE_ORIGINAL_RELIABLE_WIRE_BYTES_STAGED_NOT_QOS_PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("disposable_pinned_original_yt130_checkout",type=Path)
    apply(p.parse_args().disposable_pinned_original_yt130_checkout)
