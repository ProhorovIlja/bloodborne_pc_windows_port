/* SPDX-License-Identifier: GPL-2.0-or-later
 * V406: actual native UDP transport ENDPOINT for the original YT server.
 * One bound ephemeral UDP socket per session. NOT bound to Bloodborne's
 * existing BBHost P2P port 3658, avoiding conflicting SO_REUSEADDR readers.
 * This socket will also need to carry any future authorized direct peer
 * traffic. Until then its ONLY permitted destination is the pinned server.
 * NO authentication in this file: before consuming a received datagram
 * the caller MUST run V401 Noise NK, V403 outer SHLK and room policy.
 * No background thread, server/login auto-connection or production config.
 */
#ifndef SHYT_YT_UDP_ENDPOINT_V406_H
#define SHYT_YT_UDP_ENDPOINT_V406_H
#include <stddef.h>
#include <stdint.h>
#define SHYT_YT_UDP_MAX_DATAGRAM_V406 2048u
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytYtUdpEndpointV406 ShytYtUdpEndpointV406;
/* All IPv4 addresses/ports are network byte order, as sockaddr_in.
 * Never accepts zero/broadcast/multicast server IPs or port zero.
 * The socket itself binds an OS-assigned local ephemeral port.
 */
ShytYtUdpEndpointV406 *shyt_yt_udp_open_v406(
    uint32_t server_ipv4_nbo,uint16_t server_port_nbo);
void shyt_yt_udp_close_v406(ShytYtUdpEndpointV406 *socket);
/* Source-only local helper for a local loopback/staging server. */
int shyt_yt_udp_local_port_v406(
    const ShytYtUdpEndpointV406 *socket,uint16_t *port_nbo);
/* Sends ONLY a valid original-YT SHLK datagram to configured server.
 * Return 1 if OS accepted the datagram for transmission, not proof that
 * server saw, authenticated, accepted, or relayed it.
 */
int shyt_yt_udp_send_server_v406(
    ShytYtUdpEndpointV406 *socket,const uint8_t *packet,size_t size);
/* Nonblocking 1 packet received from the exact configured server.
 * Returns 1 with *got>0, 0 for no packet or any rejected datagram,
 * -1 for genuine local OS socket failure. Always *got=0 otherwise.
 * A valid SHLK header does NOT imply a valid encrypted session.
 */
int shyt_yt_udp_receive_server_v406(
    ShytYtUdpEndpointV406 *socket,
    uint8_t *packet,size_t packet_capacity,size_t *got);
#ifdef __cplusplus
}
#endif
#endif
