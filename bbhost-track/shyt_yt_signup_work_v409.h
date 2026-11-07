/* SPDX-License-Identifier: GPL-2.0-or-later
 * V409: real upstream YT SHLK4 hosted-new-account Proof-of-Work.
 * Entire SHA256(cookie, online_id, nonce) search runs on ONE cancellable
 * worker thread, never on BBHost's game/on_frame/network poll thread.
 * Allows original YT work difficulty 1..28 (limit intentional, server
 * supports up to 40). Bounded attempts, no retries beyond caller opt-in.
 * NEVER treat unsigned Work/Redirect as valid, see V408 Noise verifier.
 */
#ifndef SHYT_YT_SIGNUP_WORK_V409_H
#define SHYT_YT_SIGNUP_WORK_V409_H
#include <stdint.h>
#include <stddef.h>
#include "shyt_yt_shlk_client_v401.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytYtSignupWorkV409 ShytYtSignupWorkV409;
/* Return NULL for malformed/beyond-cap request or worker-start failure.
 * Hard ceiling 2^29 original YT SHA256 attempts; no background work on
 * creation of a regular/previously registered account. */
ShytYtSignupWorkV409 *shyt_yt_work_start_v409(
    const uint8_t cookie[16],const char* online_id,
    int bits,uint64_t max_attempts);
/* 0 working, 1 solved, -1 exhausted/error, -2 cancelled; nonce only on 1. */
int shyt_yt_work_poll_v409(
    const ShytYtSignupWorkV409* work,uint64_t* out_nonce);
void shyt_yt_work_cancel_v409(ShytYtSignupWorkV409* work);
void shyt_yt_work_free_v409(ShytYtSignupWorkV409* work);
/* These three functions use the very SAME upstream LinkAuth::Client that
 * V401 uses for authenticated Work/Hello. No duplicate protocol state. */
int shyt_yt_shlk_work_challenge_v409(ShytYtShlkClientV401* link,int bits);
int shyt_yt_shlk_work_complete_v409(
    ShytYtShlkClientV401* link,const uint8_t cookie[16],
    const char* online_id,int bits,uint64_t nonce);
int shyt_yt_shlk_work_nonce_v409(
    const ShytYtShlkClientV401* link,uint64_t* nonce);
#ifdef __cplusplus
}
#endif
#endif
