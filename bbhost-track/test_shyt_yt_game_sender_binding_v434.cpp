// SPDX-License-Identifier: GPL-2.0-or-later
// Actual original YT v1.4.0 GameFrame wire codec is the test oracle.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#include "shyt_yt_game_sender_binding_v434.h"
#pragma GCC diagnostic pop
#include <cassert>
#include <cstdio>
#include <vector>
#include <string>

using Guard=SeamlessHunt::YtGameSenderBindingV434;
using Status=Guard::Status;
using BloodborneCoop::GameFrame;
using BloodborneCoop::GameFrameEntry;
using BloodborneCoop::PacketClass;
using Bytes=std::vector<std::uint8_t>;

static Bytes Native(std::uint32_t ch,std::size_t count) {
    Bytes b{
        static_cast<std::uint8_t>(ch),static_cast<std::uint8_t>(ch>>8u),
        static_cast<std::uint8_t>(ch>>16u),static_cast<std::uint8_t>(ch>>24u),
        static_cast<std::uint8_t>(count),static_cast<std::uint8_t>(count>>8u),
        static_cast<std::uint8_t>(count>>16u),static_cast<std::uint8_t>(count>>24u)
    };
    for(std::size_t i=0;i<count;++i)
        b.push_back(static_cast<std::uint8_t>(i&255u));
    return b;
}
static GameFrame Roundtrip(const GameFrame& frame) {
    const auto wire=BloodborneCoop::EncodeGameFrame(frame);
    const auto decoded=BloodborneCoop::DecodeGameFrame(wire);
    assert(decoded && *decoded==frame);
    return *decoded;
}
int main() {
    GameFrame frame{"hunter2",7u,5u,3u,{}};
    frame.entries={
        {PacketClass::Unreliable,1u,Native(0x06u,8u)},
        {PacketClass::Reliable,  2u,Native(0x0fu,16u)},
        {PacketClass::Reliable,  3u,Native(68u,0u)}
    };
    const auto base=Roundtrip(frame);
    assert(Guard::Inspect(base,"hunter2",7u)==Status::Accepted);
    assert(Guard::Inspect(base,"hunter2")==Status::Accepted);
    assert(Guard::Inspect(base,"hunter3")==Status::SpoofedSender);
    assert(Guard::Inspect(base,"HUNTER2")==Status::SpoofedSender);
    assert(Guard::Inspect(base,"")==Status::MissingLinkIdentity);
    assert(Guard::Inspect(base,"hun\nter2")==Status::MissingLinkIdentity);
    assert(Guard::Inspect(base,"hunter2",9u)==Status::StaleRun);
    assert(Guard::Inspect(base,"hunter2",1u)==Status::StaleRun);

    // ACK/keepalive with zero entries is a valid original frame;
    // sequence/peer-instance are passed to the real GameLinkPeer only
    // after a trusted stream, never treated as identity proofs here.
    auto ack=base;ack.entries.clear();
    assert(Guard::Inspect(Roundtrip(ack),"hunter2")==Status::Accepted);
    auto replay=base;replay.instance=0;
    assert(Guard::Inspect(Roundtrip(replay),"hunter2")==Status::InvalidRun);
    replay.instance=6u;
    assert(Guard::Inspect(Roundtrip(replay),"hunter2")==Status::InvalidRun);

    auto spoof=base;spoof.sender="hunter3";
    assert(Guard::Inspect(Roundtrip(spoof),"hunter2")==Status::SpoofedSender);
    spoof.sender=""; // original codec accepts empty but link guard doesn't
    assert(Guard::Inspect(Roundtrip(spoof),"hunter2")==Status::SpoofedSender);
    spoof.sender=std::string("hunter2\\0bad",11u);
    assert(Guard::Inspect(Roundtrip(spoof),"hunter2")==Status::SpoofedSender);
    spoof.sender=std::string(17u,'a');
    assert(Guard::Inspect(Roundtrip(spoof),"hunter2")==Status::SpoofedSender);

    auto bad=base;
    bad.entries[0].packet[4u]=9u; // wrong original native length
    assert(Guard::Inspect(Roundtrip(bad),"hunter2")==Status::InvalidEntries);
    bad=base;bad.entries[0].packet.resize(7u);
    assert(Guard::Inspect(Roundtrip(bad),"hunter2")==Status::InvalidEntries);
    bad=base;bad.entries[0].packet=Native(69u,0u);
    assert(Guard::Inspect(Roundtrip(bad),"hunter2")==Status::InvalidEntries);
    bad=base;bad.entries[0].packet=Native(68u,0u); // tombstone reliable only
    assert(Guard::Inspect(Roundtrip(bad),"hunter2")==Status::InvalidEntries);
    bad=base;bad.entries[0].packet=Native(0x10u,Guard::MaxNativeBytes-7u);
    assert(Guard::Inspect(Roundtrip(bad),"hunter2")==Status::InvalidEntries);
    bad=base;bad.entries.resize(Guard::MaxEntries+1u);
    assert(Guard::Inspect(Roundtrip(bad),"hunter2")==Status::InvalidEntries);

    // Include real original YT encoder/decoder and all 68 channels
    // in both reliable and unreliable packet classes, without
    // conflating reliability with channel policy.
    unsigned accepted=0u;
    for(std::uint32_t ch=0u;ch<68u;++ch) {
        for(const auto klass:{PacketClass::Unreliable,PacketClass::Reliable}) {
            auto f=base;f.entries={{klass,ch,Native(ch,12u)}};
            if(Guard::Inspect(Roundtrip(f),"hunter2",7u)!=Status::Accepted)
                return 1;
            ++accepted;
        }
    }
    assert(accepted==136u);
    std::puts("SHYT_V434_ORIGINAL_YT_GAME_FRAME_SIGNED_IN_SENDER_AND_RUN_GUARD_PASS");
}
