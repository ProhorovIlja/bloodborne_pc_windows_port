// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V264: distinct physical UDP entry points. These are NOT the original
// YT shadNet/SHAD functions. Until server-authenticated pair grants have
// installed a V262 receiving session, all operations deny by default.
// This header is included only in the pinned source-overlay client.
#include "yt_signed_peer_ingress_v285.h"
namespace Libraries::Net {
// Socket endpoints and return address fields use network byte order.
bool P2PInstallVerifiedMovementEndpoint(
    const BloodborneCoop::SHYTHybrid::SignedPeerIngressV285& verified);
int P2PVerifiedMovementSendTo(
    const void *sealed, u32 len, u32 addr_nbo, u16 port_nbo);
int P2PVerifiedMovementRecvFrom(
    void *buffer, u32 len, u32 *addr_nbo, u16 *port_nbo);
void P2PRevokeVerifiedMovementEndpoints();
// V324: discover only our own public NAT mapping from the original
// physical UDP socket. Returned address is NOT proof of peer identity.
// A trusted operator must explicitly choose the external STUN endpoint.
bool P2PBeginReflexiveDiscovery(u32 server_addr_nbo,u16 server_port_nbo);
bool P2PTakeReflexiveDiscovery(u32* mapped_addr_nbo,u16* mapped_port_nbo);
} // namespace Libraries::Net
