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
    src=once(src,"#include <deque>","#include <functional>\n#include <array>\n#include <cstdint>\n#include <utility>\n#include <deque>")
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
        quint32 sender_game_link_instance=0, receiver_game_link_instance=0;
        // V308: authoritative LinkAuth-observed physical UDP endpoints.
        // NOT a client-supplied UDP address, NAT probe, or game vport.
        ServerLink::Endpoint sender_link{}, receiver_link{};
        // Responder's X25519 identity from its own authenticated intent.
        std::string responder_noise_static_key;
    };
    using DirectPeerIssuer = std::function<std::optional<bbcoop::Envelope>(
        const DirectPairSource&, const bbcoop::DirectPeerRequest&)>;
    // Server operator must provision BOTH a trusted pinned EdDSA
    // authority pubkey and a signer. Neither comes from peer traffic.
    void SetDirectPeerIssuer(
        DirectPeerIssuer issuer,
        const std::array<std::uint8_t,32>& authority_pub) {
        direct_peer_issuer=std::move(issuer);
        direct_peer_authority_pub=authority_pub;
    }

"""+anchor
    src=once(src,anchor,change)
    src=once(src,"        bool quiet = false;       // its link is quiet (the hub's)",
        "        bool quiet = false;       // its link is quiet (the hub's)\n"
        "        qint64 last_direct_peer_request_ms = 0; // V292 rate limit\n        // V302: last 2 minutes of spent request nonces; one per\n        // authenticated Member, bounded at 128 by the 1/s rate limit.\n        std::deque<std::pair<std::string,qint64>> spent_peer_nonces;\n"
        "        bbcoop::DirectPeerRequest peer_intent; // V295 bounded mutual opt-in\n"
        "        QString peer_intent_party;\n"
        "        quint64 peer_intent_epoch = 0;\n"
        "        quint32 peer_intent_map = 0, peer_intent_run = 0;\n"
        "        qint64 peer_intent_ms = 0;")
    marker="    BloodborneCoop::TeamLobby lobby;"
    src=once(src,marker,
        "    DirectPeerIssuer direct_peer_issuer; // V292 unset by default\n"
        "    std::array<std::uint8_t,32> direct_peer_authority_pub{};\n"
        +marker)
    return src

def source(src:str)->str:
    src=once(src,'#include "bloodborne_world.h"',
             '#include "bloodborne_world.h"\n'
             '#include "shyt_hybrid/yt_signed_peer_grant_v279.h"\n'
             '#include <QtEndian>')
    marker="""    if (envelope.has_invade_request()) {
        OnInvadeRequest(member, envelope.invade_request(), now_ms, result);
        return;
    }"""
    gate="""    if (envelope.has_direct_peer_request()) {
        // V292: real source-level gate BEFORE hostile/world dispatch.
        // No callback and no authenticated hosted link => no Direct P2P.
        const auto& request=envelope.direct_peer_request();
        // V302: mutual consent is not enough if the exact pair of
        // previously accepted client nonces can be replayed 1s later.
        // Retain bounded nonce history for at least the grant lifetime.
        const auto nonce_spent=[&](const Member& m,
                                   const std::string& n) {
            return std::any_of(m.spent_peer_nonces.begin(),
                m.spent_peer_nonces.end(),
                [&](const auto& entry) {
                    return entry.first==n && now_ms>=entry.second &&
                           now_ms-entry.second<=120'000;
                });
        };
        if (!direct_peer_issuer ||
            !BloodborneCoop::SHYTHybrid::SignedPeerGrantV279::NonZero(
                direct_peer_authority_pub) ||
            !require_authenticated_identity ||
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
            nonce_spent(member,request.request_nonce()) ||
            request.game_link_instance()==0 ||
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
        // V296: CRITICAL original YT TeamLobby contract:
        // TeamOf() returns the canonical team, whose TeamMember.state
        // is NOT dynamically refreshed. StateFor() explicitly populates
        // PLAYING/TITLE/OFFLINE in its server-authored lobby snapshot.
        // Never trust the stale state in canonical TeamOf() here.
        const bbcoop::LobbyState live_roster=lobby.StateFor(member.name);
        if (!live_roster.has_team() ||
            live_roster.team().id()!=team->id() ||
            live_roster.team().party()!=team->party())
            return;
        int sender_playing=0, recipient_playing=0;
        for (const auto& seat:live_roster.team().members()) {
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
        Member* recipient=nullptr;
        for (auto& [key,other]:members) {
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
        // V295: BOTH players must explicitly opt in through the
        // original authenticated shadNet Coop stream, within 12s,
        // for this exact world, epoch, map, run and reciprocal peer.
        // A solo request is never evidence of recipient consent.
        const quint64 world_epoch=
            WorldLogEpoch(world->second.world,world->second.logs);
        const bool reciprocal=
            recipient->peer_intent.recipient()==member.name &&
            recipient->peer_intent.noise_static_public_key().size()==32 &&
            recipient->peer_intent.request_nonce().size()==16 &&
            recipient->peer_intent.game_link_instance()!=0 &&
            recipient->peer_intent_party==member.party &&
            recipient->peer_intent_epoch==world_epoch &&
            recipient->peer_intent_map==member.map &&
            recipient->peer_intent_run==recipient->run &&
            recipient->peer_intent_ms>0 &&
            now_ms>=recipient->peer_intent_ms &&
            now_ms-recipient->peer_intent_ms<=12'000 &&
            recipient->peer_intent.noise_static_public_key()!=
                request.noise_static_public_key() &&
            recipient->peer_intent.request_nonce()!=request.request_nonce();
        if (!reciprocal) {
            member.peer_intent=request;
            member.peer_intent_party=member.party;
            member.peer_intent_epoch=world_epoch;
            member.peer_intent_map=member.map;
            member.peer_intent_run=member.run;
            member.peer_intent_ms=now_ms;
            return; // no issued peer grant until reciprocal request
        }
        // V308: authoritative LinkAuth observed UDP endpoints are held
        // by Service::Receive in its existing endpoint map, keyed by
        // the authenticated member's link key. No client IP claims.
        const auto sender_link=endpoints.find(member.key);
        const auto receiver_link=endpoints.find(recipient->key);
        if (sender_link==endpoints.end() ||
            receiver_link==endpoints.end() ||
            sender_link->second.Key()!=member.key ||
            receiver_link->second.Key()!=recipient->key ||
            sender_link->second==receiver_link->second ||
            !sender_link->second.ipv4 || !sender_link->second.port ||
            !receiver_link->second.ipv4 || !receiver_link->second.port)
            return; // refuse to sign without BOTH live server links
        // V295: consume the earlier player's consent BEFORE invoking
        // the external issuer. Replayed/duplicated requests cannot
        // reuse old consent or trigger a second grant.
        const bbcoop::DirectPeerRequest previous=recipient->peer_intent;
        if (nonce_spent(*recipient,previous.request_nonce()))
            return;
        // Spend both nonces BEFORE calling the external signer, including
        // unsuccessful signing attempts. Bound memory even on busy hubs.
        const auto spend=[&](Member& target,const std::string& nonce) {
            auto& entries=target.spent_peer_nonces;
            while(!entries.empty() &&
                  (now_ms<entries.front().second ||
                   now_ms-entries.front().second>120'000))
                entries.pop_front();
            if(entries.size()==128) entries.pop_front();
            entries.emplace_back(nonce,now_ms);
        };
        spend(member,request.request_nonce());
        spend(*recipient,previous.request_nonce());
        recipient->peer_intent.Clear();
        recipient->peer_intent_party.clear();
        recipient->peer_intent_epoch=0;
        recipient->peer_intent_ms=0;
        member.peer_intent.Clear();
        member.peer_intent_party.clear();
        member.peer_intent_epoch=0;
        member.peer_intent_ms=0;
        DirectPairSource authoritative{
            team->id(),team->party(),member.name,recipient->name,
            member.run,recipient->run,member.map,world_epoch,
            request.game_link_instance(),previous.game_link_instance(),
            sender_link->second,receiver_link->second,
            previous.noise_static_public_key()};
        // Callback signs ONLY the server-observed sender/receiver links
        // and the responder key from that responder's own authenticated
        // request. A real signer still needs OS CSPRNG private key/nonce
        // provisioning; NAT reachability is separate from observed link.
        const auto issued=direct_peer_issuer(authoritative,request);
        const DirectPairSource reverse{
            authoritative.team,authoritative.party,
            authoritative.receiver,authoritative.sender,
            authoritative.receiver_run,authoritative.sender_run,
            authoritative.map,authoritative.world_epoch,
            authoritative.receiver_game_link_instance,
            authoritative.sender_game_link_instance,
            authoritative.receiver_link,authoritative.sender_link,
            request.noise_static_public_key()};
        const auto issued_reverse=direct_peer_issuer(reverse,previous);
        const auto valid_envelope=[](const std::optional<bbcoop::Envelope>& e) {
            return e && e->has_direct_peer_grant() &&
                !e->direct_peer_grant().signed_grant().empty() &&
                e->direct_peer_grant().signed_grant().size()<=512 &&
                e->direct_peer_grant().authority_public_key().size()==32;
        };
        if (!valid_envelope(issued) || !valid_envelope(issued_reverse))
            return; // neither participant receives a one-sided grant
        // V294: even an operator-supplied issuer callback is not
        // permitted to redirect the player to a different signed pair,
        // map, world epoch or EdDSA authority. Verify the actual signed
        // bytes with the server's independently pinned authority key.
        namespace Grant=BloodborneCoop::SHYTHybrid::SignedPeerGrantV279;
        const auto& sent=issued->direct_peer_grant();
        // std::string bytes are char (often signed), while the public
        // key is uint8_t: compare as raw octets, including 0x80..0xff.
        const auto* returned_key=reinterpret_cast<const std::uint8_t*>(
            sent.authority_public_key().data());
        if (!std::equal(direct_peer_authority_pub.begin(),
                        direct_peer_authority_pub.end(),returned_key))
            return;
        const auto* payload=reinterpret_cast<const u8*>(
            sent.signed_grant().data());
        const auto signed_scope=Grant::DecodeWire(
            std::span<const u8>(payload,sent.signed_grant().size()));
        const Grant::Expect live{
            authoritative.team,authoritative.party,
            authoritative.sender,authoritative.receiver,
            authoritative.sender_game_link_instance,
            authoritative.receiver_game_link_instance,
            authoritative.map,authoritative.world_epoch};
        if (!signed_scope || !Grant::Verify(
                *signed_scope,direct_peer_authority_pub,live,
                QDateTime::currentMSecsSinceEpoch()) ||
            signed_scope->scope.sender_ip_nbo!=
                qToBigEndian(authoritative.sender_link.ipv4) ||
            signed_scope->scope.sender_port_nbo!=
                qToBigEndian(authoritative.sender_link.port) ||
            signed_scope->scope.receiver_ip_nbo!=
                qToBigEndian(authoritative.receiver_link.ipv4) ||
            signed_scope->scope.receiver_port_nbo!=
                qToBigEndian(authoritative.receiver_link.port) ||
            !std::equal(signed_scope->scope.responder_noise_pub.begin(),
                        signed_scope->scope.responder_noise_pub.end(),
                        reinterpret_cast<const u8*>(
                            previous.noise_static_public_key().data())))
            return;
        const auto& reverse_body=issued_reverse->direct_peer_grant();
        const auto* reverse_key=reinterpret_cast<const std::uint8_t*>(
            reverse_body.authority_public_key().data());
        if (!std::equal(direct_peer_authority_pub.begin(),
                        direct_peer_authority_pub.end(),reverse_key))
            return;
        const auto* reverse_data=reinterpret_cast<const u8*>(
            reverse_body.signed_grant().data());
        const auto reverse_signed=Grant::DecodeWire(
            std::span<const u8>(reverse_data,reverse_body.signed_grant().size()));
        const Grant::Expect reverse_live{
            reverse.team,reverse.party,reverse.sender,reverse.receiver,
            reverse.sender_game_link_instance,
            reverse.receiver_game_link_instance,
            reverse.map,reverse.world_epoch};
        if (!reverse_signed || !Grant::Verify(
                *reverse_signed,direct_peer_authority_pub,reverse_live,
                QDateTime::currentMSecsSinceEpoch()) ||
            reverse_signed->scope.sender_ip_nbo!=
                qToBigEndian(reverse.sender_link.ipv4) ||
            reverse_signed->scope.sender_port_nbo!=
                qToBigEndian(reverse.sender_link.port) ||
            reverse_signed->scope.receiver_ip_nbo!=
                qToBigEndian(reverse.receiver_link.ipv4) ||
            reverse_signed->scope.receiver_port_nbo!=
                qToBigEndian(reverse.receiver_link.port) ||
            !std::equal(reverse_signed->scope.responder_noise_pub.begin(),
                        reverse_signed->scope.responder_noise_pub.end(),
                        reinterpret_cast<const u8*>(
                            request.noise_static_public_key().data())))
            return;
        // V295: each player receives their own ordered-pair grant in
        // the original authenticated reliable Coop stream only after
        // BOTH independent server-checked opt-ins.
        SendTo(member,*issued,now_ms);
        SendTo(*recipient,*issued_reverse,now_ms);
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
        # Preserve header dependency closure in the disposable server
        # checkout; never require global mutable include directories.
        source_dir=Path(__file__).resolve().parent
        destination=root/"server/src/shyt_hybrid"
        if destination.is_symlink() or destination.exists():
            raise ValueError("refusing overwrite of prior peer source overlay")
        dependencies=(
            "hybrid_transport_policy_v1.h",
            "hybrid_direct_ingress_v2.h",
            "hybrid_direct_egress_v240.h",
            "hybrid_peer_crypto_v241.h",
            "yt_signed_peer_grant_v279.h",
        )
        for filename in dependencies:
            src=source_dir/filename
            if src.is_symlink() or not src.is_file():
                raise ValueError("missing signed grant verification source")
        destination.mkdir()
        for filename in dependencies:
            (destination/filename).write_bytes((source_dir/filename).read_bytes())
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
