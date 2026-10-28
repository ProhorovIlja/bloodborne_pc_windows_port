// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V91: source-only authenticated NAT probe codec & five-message proof.
// Both parties MUST first receive the SAME short-lived V90 paired SHG2
// master via their independently authenticated TLS 1.3 connections.
// This does not create/send on ANY UDP socket or activate Direct gameplay.
// Probe success only proves pair-key possession and candidate reachability;
// it does NOT authorize GameLink ACK handover or plaintext game payload.
#include "sh_pair_key_schedule_v89.hpp"
#include <array>
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <span>

namespace SeamlessHunt::Hybrid {
enum class NatProbeKindV91 : std::uint8_t {
    Challenge=1, Response=2, Confirm=3, ReadyAck=4, Receipt=5
};
struct NatProbeFrameV91 {
    NatProbeKindV91 kind=NatProbeKindV91::Challenge;
    std::uint64_t seq=0;
    std::array<std::uint8_t,16> nonce{};
    std::array<std::uint8_t,16> echo{};
};
class NatProbeCodecV91 final {
public:
    static constexpr std::size_t kSignedBytes=128;
    static constexpr std::size_t kTagBytes=16;
    static constexpr std::size_t kWireBytes=kSignedBytes+kTagBytes;
    using Wire=std::array<std::uint8_t,kWireBytes>;
    using Nonce=std::array<std::uint8_t,16>;

    static bool FreshNonce(Nonce& out) noexcept {
        out.fill(0);
        if(!SecureOfferV84Detail::Random(out) ||
           !SecureOfferV84Detail::Nonzero(out)) {
            out.fill(0);return false;
        }
        return true;
    }
    static bool Encode(const SecurePeerOfferV84& grant,
                       const NatProbeFrameV91& frame,
                       std::uint64_t now_ms,Wire& out) noexcept {
        out.fill(0);
        if(!SecureOfferV84Detail::Valid(grant,now_ms) || !Good(frame))
            return false;
        out[0]='S';out[1]='H';out[2]='N';out[3]='1';out[4]=1;
        out[5]=static_cast<std::uint8_t>(frame.kind);
        // 6,7 reserved zero
        Write(out,8,grant.pair_binding);
        Write(out,16,grant.world_revision);
        // sender = local game, receiver = trusted peer in our grant.
        std::copy(grant.recipient_account.begin(),
                  grant.recipient_account.end(),out.begin()+24);
        std::copy(grant.sender_account.begin(),
                  grant.sender_account.end(),out.begin()+56);
        Write(out,88,frame.seq);
        std::copy(frame.nonce.begin(),frame.nonce.end(),out.begin()+96);
        std::copy(frame.echo.begin(),frame.echo.end(),out.begin()+112);
        std::array<std::uint8_t,32> key{},digest{};
        const bool ok=PairKeyScheduleV89::Derive(
            grant,true,PairKeyPurposeV89::NatProbe,now_ms,key) &&
            CryptoDetail::Sha256Hmac(
                key,std::span<const std::uint8_t>(out.data(),kSignedBytes),digest);
        if(ok)std::copy_n(digest.begin(),kTagBytes,out.begin()+kSignedBytes);
        CryptoDetail::Erase(key);CryptoDetail::Erase(digest);
        if(!ok)out.fill(0);
        return ok;
    }

    // source_ip/source_port MUST originate from recvfrom() of the SAME
    // existing native game UDP socket; never from an untrusted packet.
    // For V91 initial safe candidate proof require exact server-captured
    // address/port; remapped NAT candidates need a separately signed offer.
    class Receiver final {
    public:
        bool Open(const SecurePeerOfferV84& grant,
                  std::uint32_t source_ip_nbo,
                  std::uint16_t source_port_nbo,
                  std::span<const std::uint8_t> wire,
                  std::uint64_t now_ms,NatProbeFrameV91& out) noexcept {
            out={};
            if(!SecureOfferV84Detail::Valid(grant,now_ms) ||
               source_ip_nbo!=grant.peer_ipv4_nbo ||
               source_port_nbo!=grant.peer_port_nbo ||
               wire.size()!=kWireBytes || wire[0]!='S' ||
               wire[1]!='H' || wire[2]!='N' || wire[3]!='1' ||
               wire[4]!=1 || wire[6] || wire[7] ||
               Read(wire,8)!=grant.pair_binding ||
               Read(wire,16)!=grant.world_revision ||
               !std::equal(grant.sender_account.begin(),
                           grant.sender_account.end(),wire.begin()+24) ||
               !std::equal(grant.recipient_account.begin(),
                           grant.recipient_account.end(),wire.begin()+56))
                return false;
            const auto kind=static_cast<NatProbeKindV91>(wire[5]);
            NatProbeFrameV91 decoded{};
            decoded.kind=kind;decoded.seq=Read(wire,88);
            std::copy_n(wire.begin()+96,16,decoded.nonce.begin());
            std::copy_n(wire.begin()+112,16,decoded.echo.begin());
            if(!Good(decoded))return false;
            std::array<std::uint8_t,32> key{},digest{};
            const bool tagged=PairKeyScheduleV89::Derive(
                grant,false,PairKeyPurposeV89::NatProbe,now_ms,key) &&
                CryptoDetail::Sha256Hmac(key,wire.first(kSignedBytes),digest) &&
                CryptoDetail::EqualTag(
                    std::span<const std::uint8_t>(digest.data(),kTagBytes),
                    wire.last(kTagBytes));
            CryptoDetail::Erase(key);CryptoDetail::Erase(digest);
            if(!tagged || !Fresh(decoded.seq))return false;
            out=decoded;return true;
        }
        void Reset() noexcept {
            high_=0;window_=0;
        }
    private:
        bool Fresh(std::uint64_t seq) noexcept {
            if(seq>high_){
                const auto delta=seq-high_;
                window_=delta>=64?1ULL:((window_<<delta)|1ULL);
                high_=seq;return true;
            }
            const auto diff=high_-seq;
            if(diff>=64 || (window_ & (1ULL<<diff)))return false;
            window_|=1ULL<<diff;return true;
        }
        std::uint64_t high_=0,window_=0;
    };
private:
    static bool Good(const NatProbeFrameV91& f) noexcept {
        const auto kind=static_cast<std::uint8_t>(f.kind);
        if(kind<1 || kind>5 || !f.seq ||
           !SecureOfferV84Detail::Nonzero(f.nonce))return false;
        const bool echo=SecureOfferV84Detail::Nonzero(f.echo);
        return kind==1?!echo:echo;
    }
    static void Write(Wire& out,std::size_t at,std::uint64_t n) noexcept {
        for(unsigned i=0;i<8;++i) {
            out[at+i]=static_cast<std::uint8_t>(n);
            n>>=8U;
        }
    }
    static std::uint64_t Read(std::span<const std::uint8_t> x,
                              std::size_t at) noexcept {
        std::uint64_t n=0;
        for(unsigned i=0;i<8;++i)n|=std::uint64_t(x[at+i])<<(8U*i);
        return n;
    }
};

// The proof state MUST NOT be interpreted as game routing permission. Only
// server's paired readiness ACK + encrypted reliable stream handover can do
// that in a future version. Never log or reuse either random nonce.
class NatProbeProofV91 final {
public:
    enum class Role :std::uint8_t { Initiator, Responder };
    explicit NatProbeProofV91(Role role):role_(role){}
    ~NatProbeProofV91(){Reset();}
    NatProbeProofV91(const NatProbeProofV91&)=delete;
    NatProbeProofV91& operator=(const NatProbeProofV91&)=delete;

    bool Start(const SecurePeerOfferV84& grant,
               std::uint64_t now_ms) noexcept {
        Reset();
        if(!SecureOfferV84Detail::Valid(grant,now_ms) ||
           !NatProbeCodecV91::FreshNonce(mine_))return false;
        grant_=grant;active_=true;stage_=0;return true;
    }
    bool Initial(std::uint64_t now_ms,NatProbeCodecV91::Wire& result) noexcept {
        result.fill(0);
        if(!active_ || role_!=Role::Initiator || stage_!=0)return false;
        NatProbeFrameV91 frame{};
        frame.kind=NatProbeKindV91::Challenge;frame.seq=1;frame.nonce=mine_;
        if(!NatProbeCodecV91::Encode(grant_,frame,now_ms,result)){
            Reset();return false;
        }
        stage_=1;return true;
    }
    // A responder: receive A challenge, reply with new B nonce and A echo.
    // An initiator: receive B response, send A confirm with B echo.
    // A responder: receive A confirm, send B ReadyAck with A echo.
    // Initiator sends a final signed Receipt after B ReadyAck.
    // Responder must verify it; neither proof enables game Direct.
    bool Reply(std::span<const std::uint8_t> received,
               std::uint32_t source_ip_nbo,
               std::uint16_t source_port_nbo,
               std::uint64_t now_ms,
               NatProbeCodecV91::Wire& response) noexcept {
        response.fill(0);
        if(!active_ || complete_)return false;
        NatProbeFrameV91 received_frame{};
        if(!receiver_.Open(grant_,source_ip_nbo,source_port_nbo,
                           received,now_ms,received_frame))return false;
        NatProbeFrameV91 outgoing{};
        if(role_==Role::Responder && stage_==0 &&
           received_frame.kind==NatProbeKindV91::Challenge) {
            other_=received_frame.nonce;
            outgoing.kind=NatProbeKindV91::Response;
            outgoing.seq=1;outgoing.nonce=mine_;outgoing.echo=other_;
            stage_=1;
        } else if(role_==Role::Initiator && stage_==1 &&
                  received_frame.kind==NatProbeKindV91::Response &&
                  received_frame.echo==mine_) {
            other_=received_frame.nonce;
            outgoing.kind=NatProbeKindV91::Confirm;
            outgoing.seq=2;outgoing.nonce=mine_;outgoing.echo=other_;
            stage_=2;
        } else if(role_==Role::Responder && stage_==1 &&
                  received_frame.kind==NatProbeKindV91::Confirm &&
                  received_frame.echo==mine_ &&
                  received_frame.nonce==other_) {
            outgoing.kind=NatProbeKindV91::ReadyAck;
            outgoing.seq=2;outgoing.nonce=mine_;outgoing.echo=other_;
            stage_=2;
            // Responder only knows that it *sent* ReadyAck; do not
            // advertise full reachability without a peer confirmation.
        } else {
            return false;
        }
        if(!NatProbeCodecV91::Encode(grant_,outgoing,now_ms,response)){
            Reset();return false;
        }
        return true;
    }
    // Fifth message: a valid ReadyAck must not be confused with both-sided
    // reachability. Do not commit a route until receipt sendto succeeds.
    bool Complete(std::span<const std::uint8_t> received,
                  std::uint32_t source_ip_nbo,std::uint16_t source_port_nbo,
                  std::uint64_t now_ms,NatProbeCodecV91::Wire& receipt) noexcept {
        receipt.fill(0);
        if(!active_ || role_!=Role::Initiator || stage_!=2 ||
           complete_)return false;
        NatProbeFrameV91 frame{};
        if(!receiver_.Open(grant_,source_ip_nbo,source_port_nbo,
                           received,now_ms,frame) ||
           frame.kind!=NatProbeKindV91::ReadyAck ||
           frame.echo!=mine_ || frame.nonce!=other_)return false;
        NatProbeFrameV91 outgoing{};
        outgoing.kind=NatProbeKindV91::Receipt;outgoing.seq=3;
        outgoing.nonce=mine_;outgoing.echo=other_;
        if(!NatProbeCodecV91::Encode(grant_,outgoing,now_ms,receipt))
            return false;
        receipt_wire_=receipt;stage_=3;
        return true;
    }
    // Only the exact grant-bound datagram handed to the native socket may
    // confirm successful send. This also defeats an old send callback
    // after the grant was revoked and replaced.
    bool ReceiptSent(std::span<const std::uint8_t> sent) noexcept {
        if(!active_ || role_!=Role::Initiator || stage_!=3 ||
           complete_ || sent.size()!=receipt_wire_.size() ||
           !std::equal(sent.begin(),sent.end(),receipt_wire_.begin()))
            return false;
        complete_=true;receipt_wire_.fill(0);return true;
    }
    bool CompleteResponder(std::span<const std::uint8_t> received,
                           std::uint32_t source_ip_nbo,
                           std::uint16_t source_port_nbo,
                           std::uint64_t now_ms) noexcept {
        if(!active_ || role_!=Role::Responder || stage_!=2 ||
           complete_)return false;
        NatProbeFrameV91 frame{};
        if(!receiver_.Open(grant_,source_ip_nbo,source_port_nbo,
                           received,now_ms,frame) ||
           frame.kind!=NatProbeKindV91::Receipt ||
           frame.nonce!=other_ || frame.echo!=mine_)return false;
        complete_=true;return true;
    }
    bool InitiatorVerified() const noexcept {
        return active_ && complete_ && role_==Role::Initiator;
    }
    bool ResponderVerified() const noexcept {
        return active_ && complete_ && role_==Role::Responder;
    }
    void Reset() noexcept {
        CryptoDetail::Erase(grant_.direction_key);
        grant_={};
        CryptoDetail::Erase(mine_);CryptoDetail::Erase(other_);
        receiver_.Reset();receipt_wire_.fill(0);
        active_=false;complete_=false;stage_=0;
    }
private:
    SecurePeerOfferV84 grant_{};
    NatProbeCodecV91::Receiver receiver_{};
    NatProbeCodecV91::Nonce mine_{},other_{};
    NatProbeCodecV91::Wire receipt_wire_{};
    Role role_;
    std::uint8_t stage_=0;
    bool active_=false,complete_=false;
};
} // namespace SeamlessHunt::Hybrid
