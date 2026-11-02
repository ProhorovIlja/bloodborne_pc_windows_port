#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V292: pin original shadNet Service::Take() server-side admission seam.

Apply to DISPOSABLE original YT v1.3.1 git checkout *after* V288
proto extension. Requests from shadNet CoopStream must prove currently
authenticated team+player+world+map/run pair. Missing server issuer => DENY.

This is NOT a ready deployment: issuer callback must be configured
by a trusted server source using original LinkAuth endpoint, V283/V289,
owner-owned CSPRNG EdDSA keys and nonce replay suppression. Never use
client-originating addresses/epoch as authoritative.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
HEADER_BLOB="c9dd02ff665b142890315e603cf28232bcdebf6a"
SOURCE_BLOB="3a28d826d52870fbaed2b8bf9a37aac51dd3cc45"
H="server/src/bloodborne_world.h"
C="server/src/bloodborne_world.cpp"

def once(data:str,before:str,after:str)->str:
    if data.count(before)!=1:
        raise ValueError("unpinned authoritative YT server hook changed")
    return data.replace(before,after,1)

def header(src:str)->str:
    src=once(src,"#include <deque>","#include <functional>\n#include <utility>\n#include <deque>")
    anchor="    void SetHosted(const HostedRules& rules);"
    change="""    // V292: production server ONLY. Default is no issuer => no P2P.
    // All fields come from currently authenticated shadNet membership,
    // live server world and server-observed map/run, not a peer packet.
    struct DirectPairSource {
        std::string team;
        std::string party;
        std::string sender;
        std::string receiver;
        quint32 sender_run=0, receiver_run=0, map=0;
        quint64 world_epoch=0;
    };
    using DirectPeerIssuer = std::function<std::optional<bbcoop::Envelope>(
        const DirectPairSource&, const bbcoop::DirectPeerRequest&)>;
    void SetDirectPeerIssuer(DirectPeerIssuer issuer) {
        direct_peer_issuer=std::move(issuer);
    }

"""+anchor
    src=once(src,anchor,change)
    src=once(src,"        bool quiet = false;       // its link is quiet (the hub's)",
        "        bool quiet = false;       // its link is quiet (the hub's)\n"
        "        qint64 last_direct_peer_request_ms = 0; // V292 rate limit")
    marker="    BloodborneCoop::TeamLobby lobby;"
    src=once(src,marker,"    DirectPeerIssuer direct_peer_issuer; // V292 deliberately unset by default\n"+marker)
    return src

def source(src:str)->str:
    marker="""    if (envelope.has_invade_request()) {
        OnInvadeRequest(member, envelope.invade_request(), now_ms, result);
        return;
    }"""
    gate="""    if (envelope.has_direct_peer_request()) {
        // V292: real source-level gate BEFORE hostile/world dispatch.
        // No callback and no authenticated hosted link => no Direct P2P.
        const auto& request=envelope.direct_peer_request();
        if (!direct_peer_issuer || !require_authenticated_identity ||
            !hosted.enabled || member.hostile || member.quiet ||
            member.name.empty() || member.lobby!=member.name ||
            member.run==0 ||
            member.map==0 || member.party.isEmpty() ||
            member.name != AuthenticatedMember(member.online_id) ||
            !OwnName(member,member.name) ||
            request.recipient().empty() || request.recipient()==member.name ||
            request.recipient().size()>64 ||
            request.noise_static_public_key().size()!=32 ||
            request.request_nonce().size()!=16 ||
            (member.last_direct_peer_request_ms &&
             now_ms-member.last_direct_peer_request_ms<1000))
            return;
        // Charge requester BEFORE any costly signing work, including
        // refused attempts. This rate limit is per original link Member.
        member.last_direct_peer_request_ms=now_ms;
        const bbcoop::Team* team=lobby.TeamOf(member.name);
        if (!team || !team->started() || team->party().empty() ||
            team->members_size()<2 ||
            team->members_size()>static_cast<int>(TeamSize))
            return;
        // Original YT TeamMember::PLAYING=2. A team row may still
        // contain players who are at TITLE/OFFLINE, not eligible for
        // any direct UDP session despite retaining team membership.
        int sender_playing=0, recipient_playing=0;
        for (const auto& seat:team->members()) {
            if (seat.member()==member.name &&
                seat.state()==bbcoop::LobbyPlayer::PLAYING)
                ++sender_playing;
            if (seat.member()==request.recipient() &&
                seat.state()==bbcoop::LobbyPlayer::PLAYING)
                ++recipient_playing;
        }
        if (sender_playing!=1 || recipient_playing!=1)
            return;
        const auto world=worlds.find(member.party);
        if (world==worlds.end() || world->second.world==0 ||
            world->second.logs==0 || world->second.team_world_id.empty() ||
            team->party()!="world:"+world->second.team_world_id)
            return;
        const Member* recipient=nullptr;
        for (const auto& [key,other]:members) {
            if (other.name==request.recipient() &&
                other.party==member.party && !other.hostile && !other.quiet &&
                other.run && other.map==member.map &&
                other.lobby==other.name &&
                other.cut_from.isEmpty() &&
                other.name==AuthenticatedMember(other.online_id) &&
                lobby.TeamOf(other.name)==team) {
                if (recipient) return; // ambiguous identity, deny
                recipient=&other;
            }
        }
        if (!recipient) return;
        DirectPairSource authoritative{
            team->id(),team->party(),member.name,recipient->name,
            member.run,recipient->run,member.map,
            WorldLogEpoch(world->second.world,world->second.logs)};
        // Caller must create signed V279 grant and derive actual peer
        // UDP endpoints and responder Noise identity from its trusted
        // server-side authenticated link registry, not from request.
        // Callback must refuse unregistered keys/nonce replay.
        const auto issued=direct_peer_issuer(authoritative,request);
        if (!issued || !issued->has_direct_peer_grant() ||
            issued->direct_peer_grant().signed_grant().empty() ||
            issued->direct_peer_grant().signed_grant().size()>512 ||
            issued->direct_peer_grant().authority_public_key().size()!=32)
            return;
        SendTo(member,*issued,now_ms); // ORIGINAL CoopStream reliable link
        return;
    }
"""
    return once(src,marker,gate+marker)

def git(root:Path,*args:str)->str:
    p=subprocess.run(["git","-C",str(root),*args],capture_output=True,
                     text=True,timeout=12)
    if p.returncode:raise ValueError("not pinned original shadNet checkout")
    return p.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=PIN:
        raise ValueError("original source SHA changed")
    files=[(H,HEADER_BLOB,header),(C,SOURCE_BLOB,source)]
    planned=[]
    for name,hash_value,modify in files:
        source_file=root/name
        if (source_file.is_symlink() or not source_file.is_file() or
            git(root,"hash-object",name)!=hash_value):
            raise ValueError("unpinned original server source")
        planned.append((source_file,modify(
            source_file.read_text(encoding="utf-8"))))
    if args.mode=="apply":
        for path,body in planned:
            path.write_text(body,encoding="utf-8")
        print("SHYT_V292_AUTHENTICATED_TEAM_WORLD_SERVER_GRANT_SEAM_DEFAULT_OFF")
    else:
        print("SHYT_V292_ORIGINAL_SERVER_ADMISSION_ANCHORS_PASS")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SystemExit("V292 refused unsafe server admission patch: "+
                         type(exc).__name__) from None
