/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_EVENT_PACKET_V619_H
#define BB_EVENT_PACKET_V619_H

typedef struct { void *self; const void *event; void *payload; } BbEventPacket619;
_Static_assert(sizeof(BbEventPacket619)==24,"event packet ABI");
#endif
