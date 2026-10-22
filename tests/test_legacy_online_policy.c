/* Offline route-policy test: no game, live server or bbnet20.dll. */
#include "../src/runtime_legacy_policy.h"
#include "../src/runtime_legacy_host.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    assert(BBNET_HOST_ABI_VERSION == 2);
    assert(sizeof(BbNetHost) == 72);
    assert(!legacy_net_opted_in(NULL,0));
    assert(!legacy_net_opted_in("true",0));
    assert(legacy_net_opted_in("1",0));
    assert(!legacy_net_opted_in("1",1));
    assert(!legacy_net_online_symbol(NULL));
    assert(!legacy_net_online_symbol("sceAudioOutOpen"));
    assert(!legacy_net_online_symbol("sceNpTrophyUnlockTrophy"));
    assert(!legacy_net_online_symbol("sceNpCommerceDialogOpen"));
    assert(!legacy_net_online_symbol("sceNpProfileDialogOpen"));
    assert(legacy_net_online_symbol("sceNpScoreCreateContext"));
    assert(legacy_net_online_symbol("sceNpPartyGetRoomInfo"));
    assert(!legacy_net_scoped_nid(NULL));
    assert(!legacy_net_scoped_nid("sceNetSocket"));
    assert(!legacy_net_scoped_nid("short#E#F"));
    assert(legacy_net_scoped_nid("Nlev7Lg8k3A#E#F"));
    assert(legacy_net_scoped_nid("z123456789A"));
    assert(!legacy_net_scoped_nid("z123456789A!E!F"));
    assert(legacy_net_online_symbol("sceNetSocket"));
    assert(legacy_net_online_symbol("sceNpMatching2JoinRoom"));
    assert(legacy_net_online_symbol("sceNpSignalingActivateConnection"));
    assert(legacy_net_online_symbol("sceHttpSendRequest"));
    assert(legacy_net_online_symbol("sceSslInit"));
    puts("BBSC legacy offline route policy: PASS");
    return 0;
}
