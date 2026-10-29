// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Authenticated, confidential direct UDP frame candidate for native Bloodborne.
// Not yet enabled in P2PTransport. The current V70 SHP1/HMAC gameplay path
// remains unarmed. A server-authenticated, peer-specific rendezvous must supply
// fresh direction-separated keys and salts; never accept keys from UDP packets.
//
// SHY2 wire: 32-byte authenticated header (magic/version/kind/epoch/pair/seq),
// AES-256-GCM ciphertext and 16-byte tag. Nonce is the server-issued UNIQUE
// four-byte direction salt followed by an unsigned 64-bit packet sequence.
// No wrapping or reusing an (AES key, salt, sequence) tuple is allowed.
// The 32-byte authenticated header prevents cross-session or cross-pair swaps.
// Sender and receiver use DIFFERENT directional keys and salts; this is one
// direction of a bidirectional link. The original virtual-peer mapping and
// path selection must still be checked outside this codec.
#include "sh_direct_datagram.hpp"
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <vector>

namespace SeamlessHunt::Hybrid {

namespace AeadDetail {
inline constexpr std::size_t HeaderBytes = 32;
inline constexpr std::size_t TagBytes = 16;
inline constexpr std::size_t NonceBytes = 12;
inline constexpr std::size_t KeyBytes = 32;
inline constexpr std::size_t SaltBytes = 4;
inline constexpr std::size_t MaxBytes = DirectReceiver::kMaxDatagramBytes;
inline constexpr std::size_t MaxPayload = MaxBytes - HeaderBytes - TagBytes;
static_assert(MaxPayload > 0 && MaxPayload <= 1184);

inline void Erase(std::span<std::uint8_t> bytes) noexcept {
    if (!bytes.empty()) OPENSSL_cleanse(bytes.data(),bytes.size());
}
inline void Store64(std::uint8_t* dest,std::uint64_t value) noexcept {
    for(unsigned i=0;i<8;++i) {
        dest[i]=static_cast<std::uint8_t>(value);
        value>>=8;
    }
}
inline std::uint64_t Load64(const std::uint8_t* src) noexcept {
    std::uint64_t v=0;
    for(unsigned i=0;i<8;++i) v|=std::uint64_t(src[i])<<(8*i);
    return v;
}
inline bool Nonzero(std::span<const std::uint8_t> bytes) noexcept {
    return std::any_of(bytes.begin(),bytes.end(),[](auto x){return x!=0;});
}
inline bool ValidTicket(const PeerTicket& p,std::int64_t now_ms) noexcept {
    return p.session_epoch && p.pair_binding && p.authenticated_sender &&
           p.local_receiver &&
           p.authenticated_sender!=p.local_receiver &&
           p.expires_at_ms>now_ms && now_ms>=0 &&
           p.server_grant_verified && p.both_consented &&
           p.version_compatible;
}
inline std::array<std::uint8_t,NonceBytes> Nonce(
    const std::array<std::uint8_t,SaltBytes>& salt,std::uint64_t seq) noexcept {
    std::array<std::uint8_t,NonceBytes> result{};
    std::copy(salt.begin(),salt.end(),result.begin());
    Store64(result.data()+SaltBytes,seq);
    return result;
}
inline bool Encrypt(const std::array<std::uint8_t,KeyBytes>& key,
                    std::span<const std::uint8_t> nonce,
                    std::span<const std::uint8_t> aad,
                    std::span<const std::uint8_t> payload,
                    std::span<std::uint8_t> encrypted,
                    std::span<std::uint8_t> tag) noexcept {
    if (nonce.size()!=NonceBytes || aad.size()!=HeaderBytes ||
        payload.size()!=encrypted.size() || tag.size()!=TagBytes ||
        payload.empty() || payload.size()>MaxPayload)
        return false;
    EVP_CIPHER_CTX* ctx=EVP_CIPHER_CTX_new();
    if(!ctx)return false;
    int n=0,m=0;
    bool ok=EVP_EncryptInit_ex(ctx,EVP_aes_256_gcm(),nullptr,nullptr,nullptr)==1;
    if(ok)ok=EVP_CIPHER_CTX_ctrl(ctx,EVP_CTRL_GCM_SET_IVLEN,
                                  static_cast<int>(nonce.size()),nullptr)==1;
    if(ok)ok=EVP_EncryptInit_ex(ctx,nullptr,nullptr,key.data(),nonce.data())==1;
    if(ok)ok=EVP_EncryptUpdate(ctx,nullptr,&n,aad.data(),
                                static_cast<int>(aad.size()))==1;
    if(ok)ok=EVP_EncryptUpdate(ctx,encrypted.data(),&n,payload.data(),
                                static_cast<int>(payload.size()))==1 &&
              n==static_cast<int>(payload.size());
    if(ok)ok=EVP_EncryptFinal_ex(ctx,encrypted.data()+n,&m)==1 && m==0;
    if(ok)ok=EVP_CIPHER_CTX_ctrl(ctx,EVP_CTRL_GCM_GET_TAG,
                                  static_cast<int>(tag.size()),tag.data())==1;
    EVP_CIPHER_CTX_free(ctx);
    return ok;
}
inline bool Decrypt(const std::array<std::uint8_t,KeyBytes>& key,
                    std::span<const std::uint8_t> nonce,
                    std::span<const std::uint8_t> aad,
                    std::span<const std::uint8_t> encrypted,
                    std::span<const std::uint8_t> tag,
                    std::span<std::uint8_t> plaintext) noexcept {
    if (nonce.size()!=NonceBytes || aad.size()!=HeaderBytes ||
        encrypted.size()!=plaintext.size() || tag.size()!=TagBytes ||
        encrypted.empty() || encrypted.size()>MaxPayload)
        return false;
    EVP_CIPHER_CTX* ctx=EVP_CIPHER_CTX_new();
    if(!ctx)return false;
    int n=0,m=0;
    bool ok=EVP_DecryptInit_ex(ctx,EVP_aes_256_gcm(),nullptr,nullptr,nullptr)==1;
    if(ok)ok=EVP_CIPHER_CTX_ctrl(ctx,EVP_CTRL_GCM_SET_IVLEN,
                                  static_cast<int>(nonce.size()),nullptr)==1;
    if(ok)ok=EVP_DecryptInit_ex(ctx,nullptr,nullptr,key.data(),nonce.data())==1;
    if(ok)ok=EVP_DecryptUpdate(ctx,nullptr,&n,aad.data(),
                                static_cast<int>(aad.size()))==1;
    if(ok)ok=EVP_DecryptUpdate(ctx,plaintext.data(),&n,encrypted.data(),
                                static_cast<int>(encrypted.size()))==1 &&
              n==static_cast<int>(encrypted.size());
    if(ok)ok=EVP_CIPHER_CTX_ctrl(ctx,EVP_CTRL_GCM_SET_TAG,
                                  static_cast<int>(tag.size()),
                                  const_cast<std::uint8_t*>(tag.data()))==1;
    if(ok)ok=EVP_DecryptFinal_ex(ctx,plaintext.data()+n,&m)==1 && m==0;
    EVP_CIPHER_CTX_free(ctx);
    if(!ok)Erase(plaintext);
    return ok;
}
inline void Header(std::span<std::uint8_t> out,
                   const PeerTicket& p,std::uint64_t sequence) noexcept {
    out[0]='S';out[1]='H';out[2]='Y';out[3]='2';
    out[4]=1;out[5]=3;out[6]=0;out[7]=0; // V1, GameData only
    Store64(out.data()+8,p.session_epoch);
    Store64(out.data()+16,p.pair_binding);
    Store64(out.data()+24,sequence);
}
inline bool HeaderValid(std::span<const std::uint8_t> wire,
                        const PeerTicket& ticket,std::uint64_t& seq) noexcept {
    if(wire.size()<HeaderBytes+TagBytes+1 || wire.size()>MaxBytes ||
       wire[0]!='S'||wire[1]!='H'||wire[2]!='Y'||wire[3]!='2' ||
       wire[4]!=1||wire[5]!=3||wire[6]!=0||wire[7]!=0 ||
       Load64(wire.data()+8)!=ticket.session_epoch ||
       Load64(wire.data()+16)!=ticket.pair_binding)return false;
    seq=Load64(wire.data()+24);
    return seq!=0;
}
} // namespace AeadDetail

class NativeGameAeadSealer final {
public:
    NativeGameAeadSealer()=default;
    ~NativeGameAeadSealer(){Revoke();}
    NativeGameAeadSealer(const NativeGameAeadSealer&)=delete;
    NativeGameAeadSealer& operator=(const NativeGameAeadSealer&)=delete;
    bool Arm(const PeerTicket& verified,
             std::span<const std::uint8_t> directional_key,
             std::span<const std::uint8_t> directional_salt,
             std::int64_t now_ms) noexcept {
        // Refuse silent rekey/sequence reset. Revoke must be explicit.
        // A fresh key/nonce also needs a NEW server-issued pair lease.
        // Explicit Revoke must not reset this local anti-nonce-reuse guard.
        if(active_ || (used_epoch_==verified.session_epoch &&
                       used_pair_==verified.pair_binding && used_epoch_) ||
           !AeadDetail::ValidTicket(verified,now_ms) ||
           directional_key.size()!=key_.size() ||
           directional_salt.size()!=salt_.size() ||
           !AeadDetail::Nonzero(directional_key) ||
           !AeadDetail::Nonzero(directional_salt))return false;
        std::copy(directional_key.begin(),directional_key.end(),key_.begin());
        std::copy(directional_salt.begin(),directional_salt.end(),salt_.begin());
        ticket_=verified;first_ms_=now_ms;next_=1;active_=true;
        used_epoch_=verified.session_epoch;used_pair_=verified.pair_binding;
        return true;
    }
    bool SealGame(std::span<const std::uint8_t> native_game_frame,
                  std::int64_t now_ms,std::vector<std::uint8_t>& out) {
        out.clear();
        if(!active_ || now_ms<first_ms_)return false;
        if(now_ms>ticket_.expires_at_ms){Revoke();return false;}
        if(next_==0 || native_game_frame.empty() ||
           native_game_frame.size()>AeadDetail::MaxPayload)return false;
        out.resize(AeadDetail::HeaderBytes+native_game_frame.size()+
                   AeadDetail::TagBytes);
        AeadDetail::Header(std::span<std::uint8_t>(out.data(),
                           AeadDetail::HeaderBytes),ticket_,next_);
        const auto nonce=AeadDetail::Nonce(salt_,next_);
        const bool ok=AeadDetail::Encrypt(
            key_,nonce,std::span<const std::uint8_t>(out.data(),AeadDetail::HeaderBytes),
            native_game_frame,
            std::span<std::uint8_t>(out.data()+AeadDetail::HeaderBytes,
                                    native_game_frame.size()),
            std::span<std::uint8_t>(out.data()+out.size()-AeadDetail::TagBytes,
                                    AeadDetail::TagBytes));
        if(!ok) {
            AeadDetail::Erase(out);out.clear();return false;
        }
        ++next_; // wraps to zero; subsequent SealGame is denied
        return true;
    }
    void Revoke() noexcept {
        AeadDetail::Erase(key_);AeadDetail::Erase(salt_);
        ticket_={};next_=0;first_ms_=0;active_=false;
    }
private:
    std::array<std::uint8_t,AeadDetail::KeyBytes> key_{};
    std::array<std::uint8_t,AeadDetail::SaltBytes> salt_{};
    PeerTicket ticket_{};
    std::uint64_t next_=0;
    std::uint64_t used_epoch_=0,used_pair_=0;
    std::int64_t first_ms_=0;
    bool active_=false;
};

class NativeGameAeadOpener final {
public:
    NativeGameAeadOpener()=default;
    ~NativeGameAeadOpener(){Revoke();}
    NativeGameAeadOpener(const NativeGameAeadOpener&)=delete;
    NativeGameAeadOpener& operator=(const NativeGameAeadOpener&)=delete;
    bool Arm(const PeerTicket& verified,
             std::span<const std::uint8_t> directional_key,
             std::span<const std::uint8_t> directional_salt,
             std::int64_t now_ms) noexcept {
        // A fresh key/nonce also needs a NEW server-issued pair lease.
        // Explicit Revoke must not reset this local anti-nonce-reuse guard.
        if(active_ || (used_epoch_==verified.session_epoch &&
                       used_pair_==verified.pair_binding && used_epoch_) ||
           !AeadDetail::ValidTicket(verified,now_ms) ||
           directional_key.size()!=key_.size() ||
           directional_salt.size()!=salt_.size() ||
           !AeadDetail::Nonzero(directional_key) ||
           !AeadDetail::Nonzero(directional_salt))return false;
        std::copy(directional_key.begin(),directional_key.end(),key_.begin());
        std::copy(directional_salt.begin(),directional_salt.end(),salt_.begin());
        ticket_=verified;first_ms_=now_ms;active_=true;
        used_epoch_=verified.session_epoch;used_pair_=verified.pair_binding;
        return true;
    }
    bool OpenGame(std::span<const std::uint8_t> datagram,
                  std::int64_t now_ms,std::vector<std::uint8_t>& native_game_frame) {
        native_game_frame.clear();
        if(!active_ || now_ms<first_ms_)return false;
        if(now_ms>ticket_.expires_at_ms){Revoke();return false;}
        std::uint64_t seq=0;
        if(!AeadDetail::HeaderValid(datagram,ticket_,seq) || Seen(seq))
            return false;
        const auto payload_len=datagram.size()-AeadDetail::HeaderBytes-
                               AeadDetail::TagBytes;
        native_game_frame.resize(payload_len);
        const auto nonce=AeadDetail::Nonce(salt_,seq);
        const bool ok=AeadDetail::Decrypt(
            key_,nonce,datagram.first(AeadDetail::HeaderBytes),
            datagram.subspan(AeadDetail::HeaderBytes,payload_len),
            datagram.last(AeadDetail::TagBytes),
            native_game_frame);
        if(!ok){
            AeadDetail::Erase(native_game_frame);
            native_game_frame.clear();
            return false;
        }
        Mark(seq); // after tag verification only; bad MAC never poisons replay
        return true;
    }
    void Revoke() noexcept {
        AeadDetail::Erase(key_);AeadDetail::Erase(salt_);
        ticket_={};first_ms_=0;highest_=0;seen_=0;active_=false;
    }
private:
    bool Seen(std::uint64_t seq) const noexcept {
        if(!highest_ || seq>highest_)return false;
        const auto behind=highest_-seq;
        return behind>=64 || (seen_ & (std::uint64_t{1}<<behind))!=0;
    }
    void Mark(std::uint64_t seq) noexcept {
        if(!highest_) {highest_=seq;seen_=1;return;}
        if(seq>highest_) {
            const auto ahead=seq-highest_;
            seen_=(ahead>=64?std::uint64_t{0}:seen_<<ahead)|1;
            highest_=seq;
        } else seen_|=std::uint64_t{1}<<(highest_-seq);
    }
    std::array<std::uint8_t,AeadDetail::KeyBytes> key_{};
    std::array<std::uint8_t,AeadDetail::SaltBytes> salt_{};
    PeerTicket ticket_{};
    std::int64_t first_ms_=0;
    std::uint64_t highest_=0,seen_=0;
    std::uint64_t used_epoch_=0,used_pair_=0;
    bool active_=false;
};
} // namespace SeamlessHunt::Hybrid
