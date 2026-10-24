# V26: bounded, lightweight inbound work per authenticated game link

Proposed mitigation for flooding thousands of small, valid protobuf envelopes.
The V24 cap prevents a single never-ending multipart message, but does not
limit decoded message rates or total bytes from multiple complete messages.

Opt-in to **strict** rooms only using SH_STRICT_MEMBER_ID_BINDING=1, which
also requires a configured ServerLink SignIn verification (V25). A small
per-linked-client O(1) token bucket is checked in Service::Receive BEFORE
DecodeEnvelope. Bursts: 240 messages and 16 MiB; refill: 120 messages/s,
approximately 4 MiB/s. A single message remains limited to 8 MiB.
No timer thread, no heap allocations, no auto-ban. Rejections logged sparsely.

Ordinary legacy protocol 7/8 PvE and active production servers do not change
while strict flag is off. A high-bandwidth legal team sync may exceed these
illustrative thresholds: stress-test co-op, reconnect and 8-MiB snapshots
before any production use, then adjust with instrumentation.

Still needed: endpoint/login quotas **before** allocating a stream, connection
limits per account/address, malformed-frame limits and authenticated role
privacy. A decoded-message quota does NOT protect lower framing code.

Standalone C++20 tests and pinned-source anchor tests; no Qt/Windows end-to-end
compile claimed.
