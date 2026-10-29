// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_direct_datagram.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;

// Deliberately NON-CRYPTOGRAPHIC test double. Production MUST replace this
// with audited, constant-time verification of per-direction HMAC-SHA256 tags.
static std::array<std::uint8_t, 16> FakeSignature(
    std::span<const std::uint8_t> bytes) {
    std::array<std::uint8_t, 16> sig{};
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        const auto j = i % sig.size();
        sig[j] = static_cast<std::uint8_t>(
            (std::uint32_t(sig[j]) * 17U + bytes[i] + 37U) & 0xFFU);
    }
    return sig;
}
struct Calls { unsigned count = 0; };
static bool TestOnlyTagCheck(std::span<const std::uint8_t> signed_bytes,
                              std::span<const std::uint8_t> tag,
                              void* context) noexcept {
    auto& calls = *static_cast<Calls*>(context);
    ++calls.count;
    const auto expected = FakeSignature(signed_bytes);
    return std::equal(expected.begin(), expected.end(), tag.begin(), tag.end());
}
static bool AlwaysReject(std::span<const std::uint8_t>,
                         std::span<const std::uint8_t>,
                         void*) noexcept { return false; }

static void U16(std::vector<std::uint8_t>& dst, std::uint16_t v) {
    dst.push_back(static_cast<std::uint8_t>(v));
    dst.push_back(static_cast<std::uint8_t>(v >> 8));
}
static void U64(std::vector<std::uint8_t>& dst, std::uint64_t v) {
    for (unsigned i = 0; i < 8; ++i)
        dst.push_back(static_cast<std::uint8_t>(v >> (8U * i)));
}
static PeerTicket Authorized() {
    PeerTicket t{};
    t.session_epoch = 300;
    t.pair_binding = 700;
    t.authenticated_sender = 11;
    t.local_receiver = 22;
    t.expires_at_ms = 20000;
    t.server_grant_verified = true;
    t.both_consented = true;
    t.version_compatible = true;
    return t;
}
static void Seal(std::vector<std::uint8_t>& data) {
    assert(data.size() >= DirectReceiver::kTagBytes);
    auto tag = FakeSignature(std::span<const std::uint8_t>(
        data.data(), data.size() - DirectReceiver::kTagBytes));
    std::copy(tag.begin(), tag.end(),
              data.end() - static_cast<std::ptrdiff_t>(tag.size()));
}
static std::vector<std::uint8_t> Wire(const PeerTicket& t, DirectKind kind,
                                      std::uint64_t seq,
                                      std::vector<std::uint8_t> payload = {}) {
    std::vector<std::uint8_t> b{'S','H','P','1',1,
        static_cast<std::uint8_t>(kind),0,0};
    U64(b,t.session_epoch);
    U64(b,t.pair_binding);
    U64(b,t.authenticated_sender);
    U64(b,t.local_receiver);
    U64(b,seq);
    U16(b,static_cast<std::uint16_t>(payload.size()));
    U16(b,0);
    assert(b.size() == DirectReceiver::kHeaderBytes);
    b.insert(b.end(),payload.begin(),payload.end());
    b.resize(b.size()+DirectReceiver::kTagBytes);
    Seal(b);
    return b;
}
static bool Accept(DirectReceiver& rx, const std::vector<std::uint8_t>& b,
                   Calls& calls, std::int64_t now = 110) {
    DirectFrame out{};
    return rx.Receive(b,now,TestOnlyTagCheck,&calls,out);
}
int main() {
    auto t = Authorized();
    DirectReceiver rx;
    Calls calls{};
    auto hello = Wire(t,DirectKind::Probe,1);
    assert(!Accept(rx,hello,calls)); // fail closed before server grant
    for (unsigned i = 0; i < 3; ++i) {
        auto bad = t;
        if (i == 0) bad.server_grant_verified = false;
        if (i == 1) bad.both_consented = false;
        if (i == 2) bad.version_compatible = false;
        assert(!rx.Arm(bad,100));
        assert(!Accept(rx,hello,calls));
    }
    assert(rx.Arm(t,100));
    assert(rx.armed());
    DirectFrame out{};
    assert(!rx.Receive(hello,110,nullptr,&calls,out)); // no MAC verifier
    assert(!rx.Receive(hello,110,AlwaysReject,&calls,out)); // false verification
    assert(Accept(rx,hello,calls));
    assert(!Accept(rx,hello,calls)); // replay
    auto payload = Wire(t,DirectKind::GameData,5,{1,2,3,4});
    assert(rx.Receive(payload,120,TestOnlyTagCheck,&calls,out));
    assert(out.kind == DirectKind::GameData && out.sequence == 5);
    assert(out.payload.size() == 4 && out.payload[0] == 1);
    assert(Accept(rx,Wire(t,DirectKind::ProbeAck,3),calls)); // valid reorder
    assert(!Accept(rx,Wire(t,DirectKind::ProbeAck,3),calls));
    assert(!Accept(rx,Wire(t,DirectKind::Heartbeat,1),calls));
    assert(Accept(rx,Wire(t,DirectKind::Heartbeat,70),calls));
    assert(!Accept(rx,Wire(t,DirectKind::Heartbeat,5),calls)); // >64 old
    assert(Accept(rx,Wire(t,DirectKind::Heartbeat,69),calls)); // reorder
    assert(!Accept(rx,Wire(t,DirectKind::Heartbeat,69),calls));

    // A tampered but unverified packet must not consume a sequence number.
    auto tampered = Wire(t,DirectKind::GameData,100,{8});
    tampered[52] ^= 1;
    const auto before = calls.count;
    assert(!Accept(rx,tampered,calls));
    assert(calls.count == before + 1);
    assert(Accept(rx,Wire(t,DirectKind::GameData,100,{8}),calls));

    // Even with a test-valid tag, session, peer and direction bind to ticket.
    auto wrong = t;
    wrong.session_epoch++;
    assert(!Accept(rx,Wire(wrong,DirectKind::Probe,101),calls));
    wrong=t;wrong.pair_binding++;
    assert(!Accept(rx,Wire(wrong,DirectKind::Probe,101),calls));
    wrong=t;wrong.authenticated_sender++;
    assert(!Accept(rx,Wire(wrong,DirectKind::Probe,101),calls));
    wrong=t;wrong.local_receiver++;
    assert(!Accept(rx,Wire(wrong,DirectKind::Probe,101),calls));

    auto bad = Wire(t,DirectKind::Probe,101);
    bad[0] = 'X';Seal(bad);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad[4] = 2;Seal(bad);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad[5] = 9;Seal(bad);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad[6] = 1;Seal(bad);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad[50] = 1;Seal(bad);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::GameData,101); // no empty game frame
    assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Heartbeat,101,{1}); // control has no payload
    assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad[48] = 255;bad[49] = 255;Seal(bad);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad.pop_back();assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,101);
    bad.push_back(0);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::Probe,0);assert(!Accept(rx,bad,calls));
    bad=Wire(t,DirectKind::GameData,101,
             std::vector<std::uint8_t>(DirectReceiver::kMaxPayloadBytes + 1,7));
    assert(!Accept(rx,bad,calls));
    assert(Accept(rx,Wire(t,DirectKind::Probe,101),calls)); // malformed did not consume
    assert(!Accept(rx,Wire(t,DirectKind::Probe,102),calls,99)); // clock rollback
    assert(Accept(rx,Wire(t,DirectKind::Probe,102),calls,20000)); // expiry boundary
    assert(!Accept(rx,Wire(t,DirectKind::Probe,103),calls,20001));
    assert(!rx.armed()); // expired grant automatically revokes direct delivery
    assert(!Accept(rx,Wire(t,DirectKind::Probe,104),calls));
    rx.Reset();
    assert(!rx.armed());
    wrong=t;wrong.local_receiver=wrong.authenticated_sender;
    assert(!rx.Arm(wrong,100)); // reflection to self disallowed
    assert(rx.Arm(t,100)); // new VERIFIED handshake resets replay state
    assert(Accept(rx,hello,calls));
    return 0;
}
