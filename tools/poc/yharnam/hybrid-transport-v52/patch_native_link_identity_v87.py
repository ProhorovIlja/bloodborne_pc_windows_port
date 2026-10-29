#!/usr/bin/env python3
"""V87: protect V86 SHG2 test against stale/mismatched ORIGINAL server link.

Source-only, same P2PTransport. FULL SHA256 computed from its own
server-welcomed online_id and compared to authenticated TLS client identity.
No trusted peer/world data is fabricated from the member notification list.
The monotonically incrementing link generation invalidates a reconnect,
even if the configured account string is exactly the same.
"""
from __future__ import annotations
NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="emulator/src/core/libraries/network/sh_native_game_identity_v87.hpp"
MARKER="SHYT-V87-TRUSTED-SERVER-LINK"

def one(s,a,b,label):
    n=s.count(a)
    if n!=1:raise ValueError(f"V87 {label}: expected exactly one pinned source anchor, got {n}")
    return s.replace(a,b,1)

def patch_game(src):
    if MARKER in src:raise ValueError("V87 already integrated")
    if ("SHYT-V86-NATIVE-FULL-ID-TLS" not in src or
        "NativeSealedGrantInboxV84 native_grant_inbox_v84" not in src):
        raise ValueError("V87 must follow V86 game-owned SHG2 integration")
    src=one(src,
        '#include "core/libraries/network/sh_native_tls_local_client_v85.hpp" // SHYT-V86-NATIVE-FULL-ID-TLS\n',
        '#include "core/libraries/network/sh_native_tls_local_client_v85.hpp" // SHYT-V86-NATIVE-FULL-ID-TLS\n'
        '#include "core/libraries/network/sh_native_game_identity_v87.hpp" // '+MARKER+'\n',
        "native test-only identity helper include")
    # Source remains exactly unchanged in default builds (compile option OFF).
    src=one(src,
        '''    std::string link_online_id;
    std::string link_secret;
''',
        '''    std::string link_online_id;
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
    // Changes under link_mutex only. Exhaustion disables identity admission.
    std::uint64_t shyt_link_generation_v87=1;
    void BumpLocalLinkGenerationV87() noexcept {
        if(shyt_link_generation_v87)++shyt_link_generation_v87;
    }
#endif
    std::string link_secret;
''',
        "original game live link identity/generation owner")
    src=one(src,
        '''            link_online_id = std::move(online_id);
            link_secret = std::move(secret);
''',
        '''            link_online_id = std::move(online_id);
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
            BumpLocalLinkGenerationV87(); // reconfigure even same online_id
#endif
            link_secret = std::move(secret);
''',
        "game ConfigureLink generation reset")
    src=one(src,
        '''        if (Link::SaysHelloAgainForBuild(link_build, build)) {
            link_welcomed = false;
            link_hello_ms.reset();
''',
        '''        if (Link::SaysHelloAgainForBuild(link_build, build)) {
            link_welcomed = false;
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
            BumpLocalLinkGenerationV87(); // version changed, require new TLS
#endif
            link_hello_ms.reset();
''',
        "game build/client protocol reset")
    src=one(src,
        '''                first = !link_welcomed;
                link_welcomed = true;
                link_refusal.clear();
''',
        '''                first = !link_welcomed;
                link_welcomed = true;
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
                if(first)BumpLocalLinkGenerationV87(); // new welcome
#endif
                link_refusal.clear();
''',
        "original server-accepted Welcome")
    src=one(src,
        '''            } else {
                repeated = link_refusal == welcome.text;
                link_refusal = welcome.text;
''',
        '''            } else {
                repeated = link_refusal == welcome.text;
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
                // A denied hello is not an authenticated game session.
                link_welcomed = false;
                BumpLocalLinkGenerationV87();
#endif
                link_refusal = welcome.text;
''',
        "server explicitly refused game Hello")
    src=one(src,
        '''            if (quiet) {
                // The server may have restarted and forgotten this game: say hello again.
                link_welcomed = false;
''',
        '''            if (quiet) {
                // The server may have restarted and forgotten this game: say hello again.
                link_welcomed = false;
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
                BumpLocalLinkGenerationV87(); // server loss revokes grant
#endif
''',
        "original heartbeat outage")
    src=one(src,
        '''        std::lock_guard lock(native_grant_mutex);
        return SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
            cfg,native_grant_inbox_v84,expected,serial,current,
            verified_game_state,now_ms);
''',
        '''        if(!running.load(std::memory_order_acquire) || LinkCut())
            return false;
        std::uint64_t original_generation=0;
        std::string original_online_id;
        bool welcomed=false,configured=false;
        {
            std::lock_guard link_lock(link_mutex);
            original_online_id=link_online_id;
            original_generation=shyt_link_generation_v87;
            welcomed=link_welcomed;
            configured=link_server.addr_nbo && link_server.port_nbo;
        }
        const bool own_identity_ok=original_generation!=0 &&
            SeamlessHunt::Hybrid::NativeGameSelfIdentityV87::MatchesAcceptedLink(
                original_online_id,welcomed,configured,expected);
        std::fill(original_online_id.begin(),original_online_id.end(),char(0));
        if(!own_identity_ok)return false;
        std::lock_guard lock(native_grant_mutex);
        const bool received=SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
            cfg,native_grant_inbox_v84,expected,serial,current,
            verified_game_state,now_ms);
        // The game may reconnect during the blocking test TLS roundtrip.
        // A same-account reconnect must NOT resurrect its previous grant.
        bool unchanged=false;
        {
            std::lock_guard link_lock(link_mutex);
            unchanged=shyt_link_generation_v87==original_generation &&
                link_welcomed && link_server.addr_nbo && link_server.port_nbo;
        }
        if(!received || !unchanged ||
           !running.load(std::memory_order_acquire) || LinkCut()) {
            native_grant_inbox_v84.Revoke();
            return false;
        }
        return true;
''',
        "game's V86 disabled-by-default TLS test call")
    return src
