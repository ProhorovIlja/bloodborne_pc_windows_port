// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Developer-side native policy only. Actual UDP socket and signed candidate
// verification MUST be implemented at the native client/server integration.
#include <algorithm>
#include <cstdint>
#include <map>
#include <string>
namespace SeamlessHunt::InGame {
enum class DataChannel { GameData, WorldControl, AccountRpc, LobbyControl };
enum class DirectState { Relay, Probing, Direct };
enum class Route { Relay, Direct };
struct RouteDecision { Route route{Route::Relay}; std::uint64_t epoch{}; };
class PeerRoutes {
public:
    explicit PeerRoutes(bool relay_only=false):relay_only_(relay_only){}
    void SetRelayOnly(bool flag) {
        if(relay_only_==flag)return;
        relay_only_=flag;
        if(flag)for(auto& [id,p]:peers_)Fallback(p);
    }
    // Call ONLY after verifying a server-signed candidate bound to room+peer+expiry.
    bool Begin(const std::string& peer,bool verified_server_candidate,
               std::int64_t now_ms,std::uint64_t attempt_nonce) {
        if(relay_only_||!verified_server_candidate||peer.empty()||attempt_nonce==0)return false;
        auto& p=peers_[peer];
        if(p.state==DirectState::Direct&&p.last_good_ms+kDeadMs>now_ms)return false;
        p.state=DirectState::Probing;p.attempt_nonce=attempt_nonce;
        p.last_probe_ms=now_ms;++p.epoch;return true;
    }
    // verified_bidirectional MUST mean authenticated UDP handshake, not an
    // untrusted boolean supplied by a remote client's HTTP request.
    bool Confirm(const std::string& peer,std::uint64_t nonce,std::uint64_t epoch,
                 bool verified_bidirectional,std::int64_t now_ms) {
        auto it=peers_.find(peer);
        if(it==peers_.end()||!verified_bidirectional)return false;
        auto& p=it->second;
        if(relay_only_||p.state!=DirectState::Probing||p.epoch!=epoch||
           p.attempt_nonce!=nonce||now_ms<p.last_probe_ms||
           now_ms-p.last_probe_ms>kProbeTimeoutMs)return false;
        p.state=DirectState::Direct;p.last_good_ms=now_ms;++p.epoch;
        return true;
    }
    void PeerAuthenticatedTraffic(const std::string& peer,std::int64_t now_ms) {
        auto it=peers_.find(peer);
        if(it!=peers_.end()&&it->second.state==DirectState::Direct)
            it->second.last_good_ms=std::max(it->second.last_good_ms,now_ms);
    }
    RouteDecision Decide(const std::string& peer,DataChannel ch)const {
        auto it=peers_.find(peer);
        const auto epoch=it==peers_.end()?0:it->second.epoch;
        // World authority, lobby and RPC never bypass the server.
        return {ch==DataChannel::GameData&&!relay_only_&&it!=peers_.end()&&
                it->second.state==DirectState::Direct ? Route::Direct : Route::Relay,epoch};
    }
    void Tick(std::int64_t now_ms) {
        for(auto& [id,p]:peers_) {
            if(p.state==DirectState::Direct&&now_ms-p.last_good_ms>=kDeadMs)Fallback(p);
            else if(p.state==DirectState::Probing&&now_ms-p.last_probe_ms>=kProbeTimeoutMs)Fallback(p);
        }
    }
    void Failed(const std::string& peer) {
        auto it=peers_.find(peer);
        if(it!=peers_.end()&&it->second.state!=DirectState::Relay)Fallback(it->second);
    }
    DirectState State(const std::string& peer)const {
        auto it=peers_.find(peer);
        return it==peers_.end()?DirectState::Relay:it->second.state;
    }
    std::uint64_t Epoch(const std::string& peer)const {
        auto it=peers_.find(peer);return it==peers_.end()?0:it->second.epoch;
    }
    static constexpr std::int64_t kProbeTimeoutMs=3500;
    static constexpr std::int64_t kDeadMs=3000;
private:
    struct Peer {
        DirectState state{DirectState::Relay};
        std::uint64_t epoch{};
        std::uint64_t attempt_nonce{};
        std::int64_t last_probe_ms{};
        std::int64_t last_good_ms{};
    };
    static void Fallback(Peer& p) {p.state=DirectState::Relay;p.attempt_nonce=0;++p.epoch;}
    bool relay_only_=false;
    std::map<std::string,Peer> peers_;
};
} // namespace SeamlessHunt::InGame
