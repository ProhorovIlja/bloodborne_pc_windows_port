// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V330: a bounded, four-datagram AUTHENTICATED-CONNECTIVITY trial.
// STUN reports an advisory reflexive endpoint; it never enables this.
// Server-signed exact pair/epoch, a pinned authority and original YT
// Noise NK are checked before a packet can be sent or processed.
//
// NK authenticates the responder only. The responder's return-path
// confirmation proves receipt of its answer and possession of derived
// keys, NOT an independent initiator identity. The fourth, encrypted ACK
// prevents the initiator from switching to direct before the responder
// has confirmed the third datagram. The original authenticated
// server pair grant, exact observed source and gameplay lease remain
// mandatory. This is a protocol fixture, not installed in live YT sockets.
#include "hybrid_peer_noise_v244.h"
#include "yt_signed_peer_grant_v279.h"
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace BloodborneCoop::SHYTHybrid::ConnectivityV327 {
namespace Grant=SignedPeerGrantV279;
namespace Noise=PeerNoiseV244;
struct Endpoint {
    u32 address_nbo=0;
    u16 port_nbo=0;
    friend bool operator==(const Endpoint&,const Endpoint&)=default;
};
constexpr s64 ProbeBudgetMs=2500;
constexpr std::array<u8,9> ConfirmHeader{
    0xff,0xff,0xff,0xff,'S','H','P','C',1};
constexpr std::size_t ConfirmWireBytes=
    ConfirmHeader.size()+32+LinkAuth::TrailerBytes;
constexpr std::array<u8,9> AckHeader{
    0xff,0xff,0xff,0xff,'S','H','P','A',1};
constexpr std::size_t AckWireBytes=
    AckHeader.size()+32+LinkAuth::TrailerBytes;

inline bool Approved(
    const Grant::Signed& signed_pair,const Grant::PubKey& pinned,
    const Grant::Expect& view,const PeerCryptoScopeV241& scope,
    const Grant::PubKey& responder_noise_pub,
    s64 unix_now_ms,s64 steady_now_ms)
{
    if(steady_now_ms<0 || steady_now_ms>
          std::numeric_limits<s64>::max()-ProbeBudgetMs)
        return false;
    return Grant::AuthorizesNoiseScope(
        signed_pair,pinned,view,unix_now_ms,scope,responder_noise_pub);
}

inline std::vector<u8> EncryptFinishProof(
    const Noise::Keys& keys,const PeerCryptoScopeV241& scope)
{
    std::vector<u8> bytes(ConfirmHeader.begin(),ConfirmHeader.end());
    const auto binding=PeerBindingV241(scope);
    bytes.insert(bytes.end(),binding.begin(),binding.end());
    LinkAuth::Session session(keys.first,keys.second);
    const auto trailer=session.Seal(bytes);
    bytes.insert(bytes.end(),trailer.begin(),trailer.end());
    return bytes;
}

inline bool AuthenticateFinishProof(
    const Noise::Keys& keys,const PeerCryptoScopeV241& scope,
    std::span<const u8> input)
{
    if(input.size()!=ConfirmWireBytes ||
       !std::equal(ConfirmHeader.begin(),ConfirmHeader.end(),input.begin()))
        return false;
    std::vector<u8> packet(input.begin(),input.end());
    LinkAuth::Session session(keys.second,keys.first);
    if(session.Open(packet)!=LinkAuth::Session::Verdict::Ok)
        return false;
    const auto binding=PeerBindingV241(scope);
    return std::equal(binding.begin(),binding.end(),
                      packet.begin()+ConfirmHeader.size());
}

inline std::vector<u8> EncryptResponderAck(
    const Noise::Keys& keys,const PeerCryptoScopeV241& scope)
{
    std::vector<u8> packet(AckHeader.begin(),AckHeader.end());
    const auto binding=PeerBindingV241(scope);
    packet.insert(packet.end(),binding.begin(),binding.end());
    LinkAuth::Session crypto(keys.second,keys.first);
    const auto trailer=crypto.Seal(packet);
    packet.insert(packet.end(),trailer.begin(),trailer.end());
    return packet;
}
inline bool AuthenticateResponderAck(
    const Noise::Keys& keys,const PeerCryptoScopeV241& scope,
    std::span<const u8> received)
{
    if(received.size()!=AckWireBytes ||
       !std::equal(AckHeader.begin(),AckHeader.end(),received.begin()))
        return false;
    std::vector<u8> packet(received.begin(),received.end());
    LinkAuth::Session crypto(keys.first,keys.second);
    if(crypto.Open(packet)!=LinkAuth::Session::Verdict::Ok)
        return false;
    const auto binding=PeerBindingV241(scope);
    return std::equal(binding.begin(),binding.end(),
                      packet.begin()+AckHeader.size());
}

class Initiator {
public:
    Initiator(PeerCryptoScopeV241 scope,
              Grant::Signed signed_pair,Grant::PubKey pinned,
              Grant::Expect view)
       : scope_(std::move(scope)),grant_(std::move(signed_pair)),
         pinned_(pinned),view_(std::move(view)),
         noise_(scope_,grant_.scope.responder_noise_pub) {}

    std::optional<std::vector<u8>> Start(
        const Noise::Key& fresh_secret,s64 unix_now_ms,s64 steady_now_ms)
    {
        if(phase_!=0 || !Approved(grant_,pinned_,view_,scope_,
             grant_.scope.responder_noise_pub,unix_now_ms,steady_now_ms))
            return std::nullopt;
        const auto hello=noise_.Start(fresh_secret);
        if(!hello)return std::nullopt;
        peer_={grant_.scope.receiver_ip_nbo,grant_.scope.receiver_port_nbo};
        expires_=steady_now_ms+ProbeBudgetMs;
        phase_=1;
        return hello;
    }
    struct Ready {
        Noise::Keys keys;
        std::vector<u8> confirm;
    };
    std::optional<Ready> OnAnswer(
        Endpoint from,std::span<const u8> answer,
        s64 unix_now_ms,s64 steady_now_ms)
    {
        if(phase_!=1 || from!=peer_ || steady_now_ms<0 ||
           steady_now_ms>expires_ ||
           !Grant::Verify(grant_,pinned_,view_,unix_now_ms))
            return std::nullopt;
        auto keys=noise_.Finish(answer);
        if(!keys)return std::nullopt;
        keys_=*keys;
        phase_=2; // pending authenticated ACK, not ready to offload
        return Ready{*keys,EncryptFinishProof(*keys,scope_)};
    }
    bool OnAcknowledge(Endpoint from,std::span<const u8> ack,
                       s64 unix_now_ms,s64 steady_now_ms)
    {
        if(phase_!=2 || !keys_ || from!=peer_ ||
           steady_now_ms<0 || steady_now_ms>expires_ ||
           !Grant::Verify(grant_,pinned_,view_,unix_now_ms) ||
           !AuthenticateResponderAck(*keys_,scope_,ack))
            return false;
        phase_=3;
        return true;
    }
    bool ReadyForDirect() const {return phase_==3;}
    void Reset() {keys_.reset();phase_=4;}
private:
    PeerCryptoScopeV241 scope_;
    Grant::Signed grant_;
    Grant::PubKey pinned_;
    Grant::Expect view_;
    Noise::Initiator noise_;
    std::optional<Noise::Keys> keys_;
    Endpoint peer_{};
    s64 expires_=0;
    int phase_=0;
};

class Responder {
public:
    Responder(PeerCryptoScopeV241 scope,
              Grant::Signed signed_pair,Grant::PubKey pinned,
              Grant::Expect view,Noise::Key static_secret)
       : scope_(std::move(scope)),grant_(std::move(signed_pair)),
         pinned_(pinned),view_(std::move(view)),
         static_pub_(LinkAuth::Noise::PublicOf(static_secret)),
         noise_(scope_,static_secret) {}
    std::optional<std::vector<u8>> OnHello(
        Endpoint from,std::span<const u8> hello,
        const Noise::Key& fresh_ephemeral,
        s64 unix_now_ms,s64 steady_now_ms)
    {
        if(phase_!=0 ||
           from!=Endpoint{grant_.scope.sender_ip_nbo,grant_.scope.sender_port_nbo} ||
           !Approved(grant_,pinned_,view_,scope_,static_pub_,
                     unix_now_ms,steady_now_ms))
            return std::nullopt;
        const auto answer=noise_.Answer(hello,fresh_ephemeral);
        if(!answer)return std::nullopt;
        peer_=from;
        keys_=answer->keys;
        expires_=steady_now_ms+ProbeBudgetMs;
        phase_=1;
        return answer->answer;
    }
    std::optional<std::vector<u8>> OnFinish(
        Endpoint from,std::span<const u8> authenticated_proof,
        s64 unix_now_ms,s64 steady_now_ms)
    {
        if(phase_!=1 || !keys_ || from!=peer_ ||
           steady_now_ms<0 || steady_now_ms>expires_ ||
           !Grant::Verify(grant_,pinned_,view_,unix_now_ms) ||
           !AuthenticateFinishProof(*keys_,scope_,authenticated_proof))
            return std::nullopt;
        phase_=2;
        return EncryptResponderAck(*keys_,scope_);
    }
    bool ReadyForDirect() const {return phase_==2;}
    void Reset() {keys_.reset();phase_=3;}
private:
    PeerCryptoScopeV241 scope_;
    Grant::Signed grant_;
    Grant::PubKey pinned_;
    Grant::Expect view_;
    Noise::Key static_pub_{};
    Noise::Responder noise_;
    std::optional<Noise::Keys> keys_;
    Endpoint peer_{};
    s64 expires_=0;
    int phase_=0;
};
} // namespace BloodborneCoop::SHYTHybrid::ConnectivityV327
