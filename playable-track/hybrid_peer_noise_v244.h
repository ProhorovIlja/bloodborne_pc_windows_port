// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V244: 2-message peer Noise NK handshake, using ORIGINAL YT v1.3.1
// LinkAuth::Noise primitives. Server MUST authenticate responder static
// public key against an exact pair/session grant BEFORE initiator Start.
// Fresh ephemeral secrets MUST come from a real OS CSPRNG and never repeat.
// This helper does not generate randomness, authorize parties, or open UDP.
#include "hybrid_peer_crypto_v241.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <optional>
#include <span>
#include <utility>
#include <vector>

namespace BloodborneCoop::SHYTHybrid {
namespace PeerNoiseV244 {
using Key = LinkAuth::Key;
using Keys = std::pair<Key,Key>; // (initiator -> responder, responder -> initiator)
constexpr size_t BindingBytes = 32;
constexpr std::array<u8, 5> Magic{'S','H','Y','N',1};
constexpr size_t WireBytes = Magic.size() + LinkAuth::KeyBytes +
                             BindingBytes + LinkAuth::TagBytes;

inline bool Nonzero(const Key& secret) {
    u8 value=0;
    for(auto c:secret) value|=c;
    return value!=0;
}
inline bool Prefix(std::span<const u8> bytes) {
    return bytes.size()==WireBytes &&
        std::equal(Magic.begin(),Magic.end(),bytes.begin());
}
inline LinkAuth::Noise::Symmetric Begin(const std::array<u8,32>& binding,
                                        const Key& responder_static_public) {
    LinkAuth::Noise::Symmetric state(binding);
    state.MixHash(responder_static_public);
    return state;
}

class Initiator {
public:
    Initiator(const PeerCryptoScopeV241& scope,
              const Key& server_approved_responder_public)
        : binding_(PeerBindingV241(scope)),
          public_key_(server_approved_responder_public),
          state_(Begin(binding_, public_key_)),
          valid_(ValidPeerCryptoScopeV241(scope) && Nonzero(public_key_)) {}

    // Must only be called ONCE; cached output may be retransmitted verbatim
    // when UDP loses the first datagram. Caller owns secure key generation.
    std::optional<std::vector<u8>> Start(const Key& ephemeral_secret) {
        if(!valid_ || started_ || !Nonzero(ephemeral_secret))
            return std::nullopt;
        const auto shared=LinkAuth::Noise::Dh(ephemeral_secret,public_key_);
        if(!shared) return std::nullopt;
        ephemeral_=ephemeral_secret;
        const Key mine=LinkAuth::Noise::PublicOf(ephemeral_);
        state_.MixHash(mine);
        state_.MixKey(*shared); // NK "es"
        std::vector<u8> first(Magic.begin(),Magic.end());
        first.insert(first.end(),mine.begin(),mine.end());
        first.insert(first.end(),binding_.begin(),binding_.end());
        std::array<u8,LinkAuth::TagBytes> tag{};
        state_.EncryptAndHash(std::span<u8>{first}.subspan(
            Magic.size()+LinkAuth::KeyBytes),tag.data());
        first.insert(first.end(),tag.begin(),tag.end());
        started_=true;
        return first;
    }

    std::optional<Keys> Finish(std::span<const u8> answer) {
        if(!started_ || finished_ || !Prefix(answer)) return std::nullopt;
        const Key peer_ephemeral=[&] {
            Key pub{};
            std::memcpy(pub.data(),answer.data()+Magic.size(),pub.size());
            return pub;
        }();
        const auto shared=LinkAuth::Noise::Dh(ephemeral_,peer_ephemeral);
        if(!shared) return std::nullopt;
        auto candidate=state_; // invalid answer cannot damage pending state
        candidate.MixHash(peer_ephemeral);
        candidate.MixKey(*shared); // NK "ee"
        auto opened=binding_;
        if(!candidate.DecryptAndHash(opened,answer.data()+WireBytes-LinkAuth::TagBytes) ||
           opened!=binding_) return std::nullopt;
        finished_=true;
        return candidate.Split();
    }
private:
    std::array<u8,32> binding_;
    Key public_key_{},ephemeral_{};
    LinkAuth::Noise::Symmetric state_;
    bool valid_=false,started_=false,finished_=false;
};

class Responder {
public:
    Responder(const PeerCryptoScopeV241& scope,
              const Key& server_approved_static_secret)
        : binding_(PeerBindingV241(scope)),
          static_secret_(server_approved_static_secret),
          static_public_(LinkAuth::Noise::PublicOf(static_secret_)),
          valid_(ValidPeerCryptoScopeV241(scope) && Nonzero(static_secret_)) {}

    struct Result {
        std::vector<u8> answer;
        Keys keys;
    };
    // Reject repeat handshakes on one responder state. Exact retransmission
    // handling and handshake replay cache must be implemented by transport.
    std::optional<Result> Answer(std::span<const u8> first,
                                  const Key& fresh_ephemeral) {
        if(!valid_ || completed_ || !Prefix(first) ||
           !Nonzero(fresh_ephemeral)) return std::nullopt;
        Key peer_ephemeral{};
        std::memcpy(peer_ephemeral.data(),first.data()+Magic.size(),
                    peer_ephemeral.size());
        const auto es=LinkAuth::Noise::Dh(static_secret_,peer_ephemeral);
        const auto ee=LinkAuth::Noise::Dh(fresh_ephemeral,peer_ephemeral);
        if(!es || !ee) return std::nullopt;
        auto state=Begin(binding_,static_public_);
        state.MixHash(peer_ephemeral);
        state.MixKey(*es);
        auto decrypted=binding_;
        if(!state.DecryptAndHash(decrypted,first.data()+WireBytes-LinkAuth::TagBytes) ||
           decrypted!=binding_) return std::nullopt;
        const Key mine=LinkAuth::Noise::PublicOf(fresh_ephemeral);
        state.MixHash(mine);
        state.MixKey(*ee);
        std::vector<u8> answer(Magic.begin(),Magic.end());
        answer.insert(answer.end(),mine.begin(),mine.end());
        answer.insert(answer.end(),binding_.begin(),binding_.end());
        std::array<u8,LinkAuth::TagBytes> tag{};
        state.EncryptAndHash(std::span<u8>{answer}.subspan(
            Magic.size()+LinkAuth::KeyBytes),tag.data());
        answer.insert(answer.end(),tag.begin(),tag.end());
        completed_=true;
        return Result{std::move(answer),state.Split()};
    }
private:
    std::array<u8,32> binding_;
    Key static_secret_{},static_public_{};
    bool valid_=false,completed_=false;
};
} // namespace PeerNoiseV244
} // namespace BloodborneCoop::SHYTHybrid
