// SPDX-License-Identifier: GPL-2.0-or-later
// Byte-for-byte actual original YT 1.3.1 server game_link.h protocol
// ↔ BBHost-safe, no-network C codec. All player IDs, maps and packets invented.
#include "coop/game_link.h"
#include "shyt_yt_game_frame_v362.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static std::uint32_t synthetic_rng_v362(std::uint32_t& state) {
    state^=state<<13;
    state^=state>>17;
    state^=state<<5;
    return state;
}
static bool decode_matches_original_v362(
    const std::vector<u8>& encoded,
    const BloodborneCoop::GameFrame& original) {
    ShytYtGameFrameV362 decoded{};
    if (!shyt_yt_game_frame_decode_v362(
          encoded.data(),encoded.size(),&decoded))
        return false;
    if (decoded.sender_len!=original.sender.size() ||
        std::memcmp(decoded.sender,original.sender.data(),
                    decoded.sender_len)!=0 ||
        decoded.instance!=original.instance ||
        decoded.peer_instance!=original.peer_instance ||
        decoded.ack!=original.ack ||
        decoded.entries_count!=original.entries.size())
        return false;
    for (std::size_t i=0;i<original.entries.size();++i) {
        const auto& a=decoded.entries[i];
        const auto& b=original.entries[i];
        if(a.packet_class!=static_cast<std::uint8_t>(b.packet_class) ||
           a.seq!=b.seq || a.packet_size!=b.packet.size() ||
           (a.packet_size && std::memcmp(a.packet,b.packet.data(),
                                         a.packet_size)!=0))
            return false;
    }
    std::array<std::uint8_t,SHYT_YT_GAME_MAX_WIRE_V362> encoded_again{};
    std::size_t result=0;
    if (!shyt_yt_game_frame_encode_v362(
          &decoded,encoded_again.data(),encoded_again.size(),&result) ||
        result!=encoded.size() ||
        std::memcmp(encoded_again.data(),encoded.data(),result)!=0)
        return false;
    return true;
}
int main() {
    using namespace BloodborneCoop;
    static_assert(GamePacketsType==SHYT_YT_GAME_PACKETS_TYPE_V362);
    static_assert(GameFrameVersion==SHYT_YT_GAME_FRAME_VERSION_V362);
    std::uint32_t state=0x5AA5B16Du;
    std::uint64_t frames=0;
    for (int t=0;t<768;++t) {
        GameFrame original{};
        original.sender="fictional-hunter-"+std::to_string(t%100);
        original.instance=synthetic_rng_v362(state);
        original.peer_instance=synthetic_rng_v362(state);
        original.ack=synthetic_rng_v362(state);
        for (int e=0;e<t%12;++e) {
            GameFrameEntry entry{};
            entry.packet_class=(e%2)?PacketClass::Reliable:PacketClass::Unreliable;
            entry.seq=synthetic_rng_v362(state);
            std::size_t n=(std::size_t)((t*37+e*19)%1001);
            entry.packet.resize(n);
            for(auto& b:entry.packet)
                b=static_cast<std::uint8_t>(synthetic_rng_v362(state)>>24);
            original.entries.push_back(std::move(entry));
        }
        const auto genuine=EncodeGameFrame(original);
        if(genuine.empty() || genuine.size()>SHYT_YT_GAME_MAX_WIRE_V362 ||
           !decode_matches_original_v362(genuine,original))
            return 11;
        ShytYtGameFrameV362 from_original{};
        from_original.sender_len=static_cast<std::uint8_t>(original.sender.size());
        std::memcpy(from_original.sender,original.sender.data(),
                    from_original.sender_len);
        from_original.instance=original.instance;
        from_original.peer_instance=original.peer_instance;
        from_original.ack=original.ack;
        from_original.entries_count=static_cast<std::uint16_t>(original.entries.size());
        for(std::size_t i=0;i<original.entries.size();++i) {
            const auto& e=original.entries[i];
            from_original.entries[i].packet_class=
                static_cast<std::uint8_t>(e.packet_class);
            from_original.entries[i].seq=e.seq;
            from_original.entries[i].packet_size=
                static_cast<std::uint32_t>(e.packet.size());
            from_original.entries[i].packet=e.packet.data();
        }
        std::array<std::uint8_t,SHYT_YT_GAME_MAX_WIRE_V362> wire{};
        std::size_t encoded_size=0;
        if(!shyt_yt_game_frame_encode_v362(&from_original,
               wire.data(),wire.size(),&encoded_size) ||
           encoded_size!=genuine.size() ||
           std::memcmp(wire.data(),genuine.data(),encoded_size)!=0)
            return 12;
        auto decoded_cpp=DecodeGameFrame(
            std::span<const u8>(wire.data(),encoded_size));
        if(!decoded_cpp || !(*decoded_cpp==original)) return 13;
        // Full source grammar must reject every truncated prefix.
        if (t==47) {
            for(std::size_t n=0;n<genuine.size();++n) {
                ShytYtGameFrameV362 invalid{};
                if(shyt_yt_game_frame_decode_v362(genuine.data(),n,&invalid))
                    return 14;
            }
            auto wrong=genuine;
            wrong[0]=99;
            ShytYtGameFrameV362 invalid{};
            if(shyt_yt_game_frame_decode_v362(
                wrong.data(),wrong.size(),&invalid)) return 15;
            wrong=genuine;
            const size_t count_at=2+original.sender.size()+12;
            wrong[count_at]=65;
            wrong[count_at+1]=0;
            if(shyt_yt_game_frame_decode_v362(
                wrong.data(),wrong.size(),&invalid)) return 16;
            wrong=genuine;
            if(!original.entries.empty()) {
                const size_t entry_at=count_at+2;
                wrong[entry_at]=0xff;
                if(shyt_yt_game_frame_decode_v362(
                    wrong.data(),wrong.size(),&invalid)) return 17;
            }
            wrong=genuine;
            wrong.push_back(0); // no trailing garbage in real YT decoder
            if(shyt_yt_game_frame_decode_v362(
                wrong.data(),wrong.size(),&invalid)) return 18;
            std::size_t written=99;
            if(shyt_yt_game_frame_encode_v362(&from_original,
                wire.data(),4,&written) || written!=0) return 19;
        }
        ++frames;
    }
    if(frames!=768) return 20;
    std::puts("SHYT_V362_REAL_YT_GAMEFRAME_ORIGINAL_CPP_VS_BBHOST_C_WIRE_768_CASES_PASS");
    std::puts("GameFrame BODY only; no SHLK v4 Noise NK, peer authorization, live game or P2P established.");
    return 0;
}
