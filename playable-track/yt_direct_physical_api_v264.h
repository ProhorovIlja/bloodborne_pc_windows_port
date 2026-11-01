// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V264: distinct physical UDP entry points. These are NOT the original
// YT shadNet/SHAD functions. Until server-authenticated pair grants have
// installed a V262 receiving session, all operations deny by default.
// This header is included only in the pinned source-overlay client.
#include "yt_game_link_direct_ingress_v262.h"
namespace Libraries::Net {
// Socket endpoints and return address fields use network byte order.
bool P2PInstallVerifiedMovementEndpoint(
    const BloodborneCoop::SHYTHybrid::VerifiedPeerIngressV262& verified);
int P2PVerifiedMovementSendTo(
    const void *sealed, u32 len, u32 addr_nbo, u16 port_nbo);
int P2PVerifiedMovementRecvFrom(
    void *buffer, u32 len, u32 *addr_nbo, u16 *port_nbo);
void P2PRevokeVerifiedMovementEndpoints();
} // namespace Libraries::Net
