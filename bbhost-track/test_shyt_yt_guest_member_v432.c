/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "shyt_yt_guest_member_v432.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const uint64_t member=UINT64_C(0x7000000);
static const uint64_t identity=UINT64_C(0x8000000);
static uint8_t np_id[SHYT_V432_SCE_NP_ID_BYTES];
static uint64_t injected_ptr;
static unsigned reads,fail_pointer,fail_identity,wrong_address;
static int fake_read(uint64_t addr,void* out,size_t n) {
    ++reads;
    if(addr==member) {
        assert(n==8u);
        if(fail_pointer)return 1;
        for(unsigned i=0u;i<8u;++i)((uint8_t*)out)[i]=
            (uint8_t)(injected_ptr>>(8u*i));
        return 0;
    }
    if(addr==identity+SHYT_V432_ID_OFFSET) {
        assert(n==SHYT_V432_SCE_NP_ID_BYTES);
        if(fail_identity)return 1;
        memcpy(out,np_id,sizeof(np_id));
        return 0;
    }
    ++wrong_address;
    return 1;
}
static void set_name(const char* text) {
    memset(np_id,0,sizeof(np_id));
    const size_t n=strlen(text);
    if(n<sizeof(np_id))memcpy(np_id,text,n);
}
int main(void) {
    ShytYtGuestMemberV432 resolved={0};
    injected_ptr=identity;
    set_name("hunter2");
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,NULL));
    assert(!shyt_yt_v432_resolve(0,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    assert(!shyt_yt_v432_resolve(1,"untrusted",fake_read,member,&resolved));
    assert(!shyt_yt_v432_resolve(1,NULL,fake_read,member,&resolved));
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                NULL,member,&resolved));
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,0u,&resolved));
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,UINT64_MAX,&resolved));
    assert(reads==0u && wrong_address==0u && !resolved.candidate_read_only);
    assert(shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                               fake_read,member,&resolved));
    assert(reads==2u && wrong_address==0u &&
           !strcmp(resolved.raw_online_id,"hunter2") &&
           !strcmp(resolved.canonical_member_hex,"68756e74657232") &&
           resolved.online_id_len==7u && resolved.candidate_read_only==1u &&
           resolved.can_route_game==0u);
    /* The original parser ignores garbage after an early NUL. */
    set_name("rig-host_1");np_id[16]=0xffu;
    assert(shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                               fake_read,member,&resolved));
    assert(!strcmp(resolved.canonical_member_hex,
                   "7269672d686f73745f31"));
    set_name("ABC123_-def"); 
    assert(shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                               fake_read,member,&resolved));
    assert(!strcmp(resolved.raw_online_id,"ABC123_-def"));
    set_name("abc");
    assert(shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                               fake_read,member,&resolved));
    assert(!strcmp(resolved.canonical_member_hex,"616263"));
    set_name("abcdefghijklmnop");
    assert(shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                               fake_read,member,&resolved));
    assert(resolved.online_id_len==16u);
    set_name("ab");
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    assert(!resolved.candidate_read_only && !resolved.raw_online_id[0]);
    set_name("a bad name");
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    set_name("abc");
    np_id[0]=0xc3u; /* UTF-8 is not valid NP OnlineID ASCII */
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    memset(np_id,'a',sizeof(np_id)); /* missing NUL at index 16 */
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    injected_ptr=UINT64_MAX;
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    injected_ptr=0u;
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    injected_ptr=identity;
    fail_pointer=1u;
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    fail_pointer=0u;fail_identity=1u;
    assert(!shyt_yt_v432_resolve(1,SHYT_V427_EXPECTED_EBOOT_SHA256,
                                fake_read,member,&resolved));
    assert(!resolved.online_id_len && !resolved.can_route_game &&
           !resolved.canonical_member_hex[0]);
    printf("SHYT_V432_ORIGINAL_YT_SCE_NP_ID_GUEST_READ_FAIL_CLOSED_PASS\n");
    return 0;
}
