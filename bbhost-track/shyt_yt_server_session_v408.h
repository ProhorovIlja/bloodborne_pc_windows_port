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
} ShytYtServerCountersV408;
/* V413 separate ABI: preserve the exact layout/size of existing V408
 * counters for older compiled BBHost plugins. No team/game authorization. */
typedef struct ShytYtCoopCountersV413 {
    uint64_t frames_reassembled;
    uint64_t frames_rejected;
    uint64_t fail_closed;
    uint64_t messages_held; /* point-in-time count, not a cumulative total */
} ShytYtCoopCountersV413;
/* V415: observed original YT lobby/team envelopes after the pinned
 * server's Noise NK and reliable CoopStream. Diagnostic only: an
 * unbound party Welcome NEVER authorizes game packets. */
typedef struct ShytYtTeamObservationsV415 {
    uint64_t lobby_states_accepted;
    uint64_t team_starts_accepted;
    uint64_t authority_messages_rejected;
    uint64_t party_welcomes_unbound;
} ShytYtTeamObservationsV415;
/* V419: diagnostics only. A correlated reply is NOT a playable world grant. */
typedef struct ShytYtPartyReplyObservationsV419 {
    uint64_t party_hellos_sent;
    uint64_t replies_correlated;
    uint64_t replies_refused;
    uint64_t replies_unbound;
    uint64_t contexts_revoked;
    uint8_t candidate_awaiting_snapshot;
} ShytYtPartyReplyObservationsV419;
/* V420: original YT SnapshotRequest/Snapshot metadata observations.
 * A matching epoch/last is NOT a validated world payload or game grant.
 * No older C ABI struct is enlarged. */
typedef struct ShytYtWorldSnapshotObservationsV420 {
    uint64_t requests_sent;
    uint64_t metadata_matching;
    uint64_t metadata_rejected;
    uint64_t metadata_unbound;
    uint64_t contexts_revoked;
    uint8_t awaiting_game_snapshot_consumer;
} ShytYtWorldSnapshotObservationsV420;
/* V423 read-only world log audit. All counters refer to authenticated,
 * structurally checked server data and NEVER to applied game-world state. */
typedef struct ShytYtWorldDeltaObservationsV423 {
    uint64_t heartbeats;
    uint64_t replays;
    uint64_t advanced;
    uint64_t gaps;
    uint64_t epoch_changes;
    uint64_t invalid;
    uint64_t unbound;
    uint64_t contexts_revoked;
    uint64_t epoch;
    uint64_t cursor;
    uint64_t server_last;
    uint8_t tracking;
    uint8_t awaiting_more;
} ShytYtWorldDeltaObservationsV423;
/* V424: count only SAFE authenticated stale-event/heartbeat pruning.
 * bytes_pruned is application-envelope staging memory, NOT WAN traffic
 * saved (original encrypted frames still arrived on the network). */
typedef struct ShytYtRedundantWorldPruningV424 {
    uint64_t heartbeats_pruned;
    uint64_t replays_pruned;
    uint64_t bytes_pruned;
    uint64_t messages_still_held;
} ShytYtRedundantWorldPruningV424;
/* V425: bounded, read-only staged original Snapshot/Entries. Cursor here
 * means only staged, NOT applied to Bloodborne or guest save memory. */
typedef struct ShytYtWorldStagingObservationsV425 {
    uint64_t snapshots_staged;
    uint64_t delta_batches_staged;
    uint64_t rejected;
    uint64_t revoked;
    uint64_t epoch;
    uint64_t staged_cursor;
    uint64_t staged_bytes;
    uint64_t pending_packets;
    uint8_t active;
} ShytYtWorldStagingObservationsV425;
/* V426 read-only, on-demand type projection. Counts are shadow world
 * data reconstructed from authenticated staging, never guest game writes.
 * Does NOT imply NetSync or save/reward application. */
typedef struct ShytYtWorldProjectionObservationsV426 {
    uint64_t epoch;
    uint64_t projected_seq;
    uint64_t game_applied_seq;
    uint64_t killed;
    uint64_t shown;
    uint64_t hp_reports;
    uint64_t hp_enemies;
    uint64_t map_state_bytes;
    uint64_t snapshot_recent_flags;
    uint64_t live_flag_events;
    uint64_t unknown_kinds;
    uint32_t shown_map;
    uint32_t map_state_map;
    int32_t return_point;
    uint32_t return_point_map;
    uint8_t after_wipe;
    uint8_t projection_ready;
} ShytYtWorldProjectionObservationsV426;
/* V431: evidence from the authenticated server's original Team Lobby,
 * checked TeamStart, correlated Hello/Welcome and matched Snapshot.
 * Every result is READ-ONLY. The source Welcome does NOT bind a peer
 * identity/endpoint, so can_arm_game_queue and can_route_game are always
 * ZERO even if all other observations are present. */
typedef struct ShytYtPeerEvidenceObservationsV431 {
    uint64_t observed_world_epoch;
    uint64_t observed_world_cursor;
    uint8_t roster_candidate;
    uint8_t correlated_hello;
    uint8_t matched_world_snapshot;
    uint8_t can_arm_game_queue;
    uint8_t can_route_game;
} ShytYtPeerEvidenceObservationsV431;


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
/* Read-only, versioned transport diagnostic. Its counters are not a
 * permission to deliver network data to the guest game. */
int shyt_yt_server_coop_counters_v413(const ShytYtServerSessionV408 *session,
                                     ShytYtCoopCountersV413 *out);
/* V415 does not expose or assert team/world authorization: until the
 * separate party-stream Hello/Welcome binding is proven, game injection
 * remains disabled and these are observation counters only. */
int shyt_yt_server_team_observations_v415(const ShytYtServerSessionV408 *session,
                                          ShytYtTeamObservationsV415 *out);
/* Correlated same-link party Welcome, still NOT world authority or NetSync. */
int shyt_yt_server_party_observations_v419(const ShytYtServerSessionV408 *session,
                                           ShytYtPartyReplyObservationsV419 *out);
/* Diagnostic only; no NetSync or world application grant. */
int shyt_yt_server_world_observations_v420(const ShytYtServerSessionV408 *session,
                                           ShytYtWorldSnapshotObservationsV420 *out);
int shyt_yt_server_world_delta_observations_v423(
    const ShytYtServerSessionV408 *session,ShytYtWorldDeltaObservationsV423 *out);
int shyt_yt_server_world_pruning_observations_v424(
    const ShytYtServerSessionV408 *session,ShytYtRedundantWorldPruningV424 *out);
int shyt_yt_server_world_staging_observations_v425(
    const ShytYtServerSessionV408 *session,ShytYtWorldStagingObservationsV425 *out);
/* Explicitly requested diagnostic only. Replays at most 128 KiB of
 * previously staged original protobuf, never runs during network tick. */
int shyt_yt_server_world_projection_observations_v426(
    const ShytYtServerSessionV408 *session,ShytYtWorldProjectionObservationsV426 *out);
/* canonical_peer_member is the hex-encoded original TeamMember.member,
 * not a player's display name or UDP source address. Read-only, on the
 * same thread as session tick(); never a P2P/NetSync permission. */
int shyt_yt_server_peer_evidence_v431(
    const ShytYtServerSessionV408 *session,const char *canonical_peer_member,
    ShytYtPeerEvidenceObservationsV431 *out);
/* V416: EXPLICIT caller-opt-in original YT Envelope{LobbyHello}.
 * Requires SHLK Noise-NK LINKED, a new empty reliable stream and a
 * well-formed UTF-8 display name (1..96 bytes). Derives the lobby member
 * from the *authenticated* online ID as lowercase hex, matching YT's
 * AuthenticatedMember; caller cannot supply/forge a member ID.
 * 1=queued/sent, 0=refused without network side effect, -1=send failure.
 * Never called automatically at plugin init; no team/world or NetSync grant.
 * The controller is single-threaded: call on the same thread as tick().
 */
int shyt_yt_server_send_lobby_hello_v416(ShytYtServerSessionV408 *session,
                                          const char *display_name,
                                          int playing,uint64_t monotonic_ms);
/* V418: opt-in original YT Envelope{Hello} for a server-validated
 * TeamStart, only after the caller has actually loaded the selected game
 * save slot. The team ID, party and host come from the authenticated
 * lobby (V414), while run/slot must be furnished by the owner game.
 * The initial SHLK Login and lobby Hello are prerequisites.
 * No implicit start, world-save write, NetSync, or peer Data permission.
 * 1=sent, 0=refused, -1=local send failure, single-threaded with tick().
 * A party Welcome is NOT yet a retail/gameplay authorization.
 */
int shyt_yt_server_send_party_hello_v418(ShytYtServerSessionV408 *session,
                                         const char *party,uint32_t loaded_slot,
                                         uint32_t game_run,int enemy_owner,
                                         uint64_t monotonic_ms);
/* V420: manually opt in to canonical original YT SnapshotRequest{epoch=0,seq=0}
 * AFTER a correlated party Welcome, over the same encrypted CoopStream.
 * No game world is applied even if Snapshot is later received.
 * 1=queued/sent, 0=not admitted, -1=local transport failure.
 */
int shyt_yt_server_send_snapshot_request_v420(ShytYtServerSessionV408 *session,
                                               uint64_t monotonic_ms);
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
