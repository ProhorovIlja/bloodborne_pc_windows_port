/* SPDX-License-Identifier: GPL-2.0-or-later
 * V408: real native, manually-driven Yharnam Together server session.
 * Runs authenticated SHLK4 Noise NK over the real V406 UDP endpoint.
 * Creation and poll require EXPLICIT caller opt-in and complete inputs.
 * Never auto-starts from BBHost plugin init or connects to owner Fornex.
 * Authenticated hosted Work executes asynchronously on a cancellable
 * original-YT SHA256 worker; redirects remain blocked pending shard
 * ticket validation.
 * Encrypted game packets are QUARANTINED until server room authorization
 * and BBHost guest NetSync callbacks are verified and implemented.
 *
 * All network addresses/ports passed here are in sockaddr_in network
 * byte order. Do not pass owner secrets, addresses or packet contents
 * to logging, CI, diagnostics or public metadata.
 */
#ifndef SHYT_YT_SERVER_SESSION_V408_H
#define SHYT_YT_SERVER_SESSION_V408_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytYtServerSessionV408 ShytYtServerSessionV408;
enum ShytYtServerPhaseV408 {
    SHYT_V408_NEW=0,
    SHYT_V408_WAIT_COOKIE=1,
    SHYT_V408_WAIT_WELCOME=2,
    SHYT_V408_LINKED=3,
    SHYT_V408_QUIET=4,
    SHYT_V408_SOLVING_WORK=5,
    SHYT_V408_REFUSED=6,
    SHYT_V408_WORK_UNSUPPORTED=7,
    SHYT_V408_REDIRECT_UNSUPPORTED=8,
    SHYT_V408_IO_FAILED=9
};
/* V412: server LINK presence notifications (Quiet / Back / Gone).
 * NOT a team/room membership authorization, P2P grant, or permission to
 * forward game packets. Read only on the same thread as tick().
 * All addresses and ports remain in network byte order.
 */
enum { SHYT_V412_MEMBER_QUEUE_CAP = 16 };
typedef struct ShytYtMemberNoticeV412 {
    uint8_t state; /* 0 Quiet, 1 Back, 2 Gone; original YT MemberState */
    uint32_t gap_ms;
    uint32_t addr_nbo;
    uint16_t port_nbo;
    char online_id[256]; /* NUL-terminated, never logged */
} ShytYtMemberNoticeV412;
typedef struct ShytYtServerCountersV408 {
    uint64_t hello_sent;
    uint64_t auth_errors;
    uint64_t heartbeats_sent;
    uint64_t heartbeats_received;
    uint64_t authenticated_data_quarantined;
    uint64_t authenticated_coop_quarantined;
    uint64_t rejected_control_packets;
    uint64_t verified_work_challenges;
    uint64_t work_nonces_solved;
    uint64_t work_challenges_refused;
    uint64_t authenticated_member_notices;
    uint64_t rejected_member_notices;
    uint64_t member_notice_overflows;
    /* V413 diagnostic only. Counts authenticated Coop datagrams whose
     * GameFrames passed original YT reliable stream parsing. Neither a
     * transport ACK nor a queued envelope authorizes a team or world.
     * The last held count is a snapshot, not a cumulative counter. */
    uint64_t coop_frames_reassembled_v413;
    uint64_t coop_frames_rejected_v413;
    uint64_t coop_fail_closed_v413;
    uint64_t coop_messages_held_v413;
} ShytYtServerCountersV408;
/* C-string fields must be present, NUL-terminated and 1..255B.
 * No implicit fallback to unsigned/TOFU key, and no credential capture.
 * Opens one independent ephemeral UDP socket, but sends NOTHING until
 * shyt_yt_server_tick_v408 is called. */
ShytYtServerSessionV408 *shyt_yt_server_new_v408(
    uint32_t server_ip_nbo,uint16_t server_port_nbo,
    const uint8_t pinned_server_pub[32],
    const char *online_id,const char *game_build,const char *secret);
void shyt_yt_server_free_v408(ShytYtServerSessionV408 *session);
/* Give a monotonic milliseconds time, no busy-loop/thread, process up
 * to 32 datagrams, retry pending hello and send encrypted heartbeat.
 * Return 1 for valid local operation, -1 for fatal local socket/RNG
 * error. A linked phase proves only crypto session, NOT team approval.
 */
int shyt_yt_server_tick_v408(ShytYtServerSessionV408 *session,
                             uint64_t monotonic_ms);
int shyt_yt_server_phase_v408(const ShytYtServerSessionV408 *session);
int shyt_yt_server_counters_v408(const ShytYtServerSessionV408 *session,
                                 ShytYtServerCountersV408 *out);
/* Consume exactly one MAC-authenticated LINK presence notice.
 * Returns 1 for a notice; 0 if empty/bad args; -1 if the bounded
 * queue overflowed, permanently invalidating presence until a NEW
 * session/snapshot. In every case except 1, *out is zeroed.
 * This API MUST NOT authorize a room or inject a P2P game packet.
 */
int shyt_yt_server_take_member_v412(
    ShytYtServerSessionV408 *session,ShytYtMemberNoticeV412 *out);
/* Exposes ephemeral local UDP port for isolated/authorized integration
 * tests; never a direct game listener and not the BBHost P2P port. */
int shyt_yt_server_local_port_v408(const ShytYtServerSessionV408 *session,
                                   uint16_t *port_nbo);
#ifdef __cplusplus
}
#endif
#endif
