/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "shyt_yt_guest_hook_preflight_v427.h"
#include <assert.h>
#include <stdio.h>

static unsigned calls,wrong_addr;
static unsigned mismatch,read_fail;
static const unsigned char source_prefix[SHYT_V427_PREFIX_LENGTH]={
    0x55u,0x48u,0x89u,0xe5u,0x41u,0x57u
};
static int fake_read(uint64_t bn,void* output,size_t n) {
    ++calls;
    if(n!=SHYT_V427_PREFIX_LENGTH ||
       (bn!=SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_TRANSPORT_SEND_RVA &&
        bn!=SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_NETSYNC_UPDATE_RVA)) {
        ++wrong_addr;
        return 1;
    }
    if(read_fail && bn==SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_NETSYNC_UPDATE_RVA)
        return 1;
    memcpy(output,source_prefix,sizeof(source_prefix));
    if(mismatch && bn==SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_NETSYNC_UPDATE_RVA)
        ((unsigned char*)output)[3]=0x90u;
    return 0;
}
int main(void) {
    ShytYtGuestHookPreflightV427 out;
    assert(shyt_yt_guest_site_bn_v427(0)==UINT64_C(0x0108F0A0));
    assert(shyt_yt_guest_site_bn_v427(1)==UINT64_C(0x01B89B60));
    assert(shyt_yt_guest_site_bn_v427(2)==0);
    assert(SHYT_V427_HOOK_INSTALL_ALLOWED==0);
    assert(!shyt_yt_guest_hook_preflight_v427(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,fake_read,NULL));
    assert(calls==0u);

    /* Wrong image is rejected *before any guest memory access*. */
    assert(!shyt_yt_guest_hook_preflight_v427(
        0,SHYT_V427_EXPECTED_EBOOT_SHA256,fake_read,&out));
    assert(!out.expected_image && !calls);
    assert(!shyt_yt_guest_hook_preflight_v427(
        1,"f000000000000000000000000000000000000000000000000000000000000000",fake_read,&out));
    assert(!out.expected_image && !calls);
    assert(!shyt_yt_guest_hook_preflight_v427(
        1,NULL,fake_read,&out));
    assert(!shyt_yt_guest_hook_preflight_v427(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,NULL,&out));
    assert(!calls);
    assert(shyt_yt_guest_hook_preflight_v427(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,fake_read,&out));
    assert(calls==2u && wrong_addr==0u &&
           out.expected_image && out.sites_read==2u &&
           out.sites_matching==2u && out.sites_mismatching==0u &&
           out.unsafe_hook_install_allowed==0u);

    /* A mod patching one site cannot enable a guessed hook. */
    mismatch=1u;calls=0u;
    assert(!shyt_yt_guest_hook_preflight_v427(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,fake_read,&out));
    assert(calls==2u && out.sites_read==2u &&
           out.sites_matching==1u && out.sites_mismatching==1u &&
           !out.unsafe_hook_install_allowed);

    /* A read failure is NOT counted as a clean matching prologue. */
    mismatch=0u;read_fail=1u;calls=0u;
    assert(!shyt_yt_guest_hook_preflight_v427(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,fake_read,&out));
    assert(calls==2u && out.sites_read==1u &&
           out.sites_matching==1u && out.sites_mismatching==0u &&
           !out.unsafe_hook_install_allowed);
    puts("SHYT_V427_109_YT_NETSYNC_HOOK_PREFLIGHT_READ_ONLY_PASS");
    return 0;
}
