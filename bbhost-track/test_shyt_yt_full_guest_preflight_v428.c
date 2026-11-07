/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "shyt_yt_full_guest_preflight_v428.h"
#include <assert.h>
#include <stdio.h>
static unsigned calls,failed_reads,mutate;
static const uint8_t transport[SHYT_V428_TRANSPORT_BYTES]={
    0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
    0x41,0x55,0x41,0x54,0x53,0x50
};
static const uint8_t update[SHYT_V428_UPDATE_BYTES]={
    0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
    0x41,0x55,0x41,0x54,0x53,0x48,0x81,0xec,
    0x18,0x21,0x00,0x00
};
static int test_read(uint64_t address,void* dst,size_t n) {
    ++calls;
    if(address==SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_TRANSPORT_SEND_RVA) {
        assert(n==sizeof(transport));
        if(failed_reads&1u)return 1;
        memcpy(dst,transport,n);
        if(mutate&1u)((uint8_t*)dst)[13u]^=1u; /* beyond V427 six-byte prefix */
        return 0;
    }
    assert(address==SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_NETSYNC_UPDATE_RVA);
    assert(n==sizeof(update));
    if(failed_reads&2u)return 1;
    memcpy(dst,update,n);
    if(mutate&2u)((uint8_t*)dst)[18u]^=1u;
    return 0;
}
int main(void) {
    ShytYtFullGuestPreflightV428 report={0};
    assert(SHYT_V428_SAFE_TO_INSTALL_YT_HOOKS==0);
    assert(!shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,NULL));
    assert(!calls);
    assert(!shyt_yt_full_guest_preflight_v428(
        0,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,&report));
    assert(!report.exact_image && !calls);
    assert(!shyt_yt_full_guest_preflight_v428(
        1,"wrong",test_read,&report));
    assert(!report.exact_image && !calls);
    assert(!shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,NULL,&report));
    assert(!calls);
    assert(shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,&report));
    assert(calls==2u && report.exact_image==1u &&
           report.transport_read==1u && report.update_read==1u &&
           report.transport_matched==1u && report.update_matched==1u &&
           !report.install_allowed);
    calls=0u;mutate=1u;
    assert(!shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,&report));
    assert(calls==2u && !report.transport_matched &&
           report.update_matched && !report.install_allowed);
    mutate=2u;
    assert(!shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,&report));
    assert(report.transport_matched && !report.update_matched);
    mutate=0u;failed_reads=1u;
    assert(!shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,&report));
    assert(!report.transport_read && report.update_read);
    failed_reads=2u;
    assert(!shyt_yt_full_guest_preflight_v428(
        1,SHYT_V427_EXPECTED_EBOOT_SHA256,test_read,&report));
    assert(report.transport_read && !report.update_read);
    puts("SHYT_V428_109_FULL_GAME_SEND_NETSYNC_PREFLIGHT_READ_ONLY_PASS");
    return 0;
}
