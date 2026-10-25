# V76-V77: coherent authoritative peer scope and no-ABA grant version

Status: source-only patches to **actual pinned Qt BloodborneWorld::Service**, exercised by the original compiled Qt/protobuf world tests. **Not a new service**, listener, deployed server, playable PC build, or active Direct session.

## V76: source of truth for a future TLS offer issuer

The original Qt server knows both the host-order *physical* UDP endpoints attached to the two authenticated shadNet account links, their persistent account-derived *virtual* game addresses, the current team and map, and the world revision.

`CaptureDirectPairScope(first_online_id, second_online_id)` now returns an **internal** `DirectPairScope` only when:
- both nonempty, different account IDs map to exactly one current linked `Member` each (duplicate identities fail closed);
- both current Yharnam Together co-op Hellos explicitly opted into Direct (legacy clients opt out);
- neither account was cut from the team and both are on the same known map with an active authoritative world;
- both real UDP endpoints and both virtual endpoints exist, differ and are well formed;
- a nonzero current server-owned world revision can be captured.

It returns the two online IDs (raw QByteArrays for internal binding, **never a username or peer-provided numeric ID**), real host-order UDP endpoints, game virtual endpoints, and their revision. This is used by `PairDirectConsent` to avoid two different definitions of eligibility. **No code copies the snapshot to a SHLK frame or an HTTP/WebAPI response.**

A future authenticated TLS control plane MUST revalidate the recipient's TLS-authenticated online_id against the exact session and this authoritative snapshot immediately before encrypting/minting a V75 peer offer. A snapshot is not itself a permission token and does not secure external APIs. Don't expose real IPs without explicit mutual consent + encrypted recipient-specific delivery.

## V77: prevent same-map/rejoin grant ABA

The original V72 deterministic world fingerprint can repeat when a player leaves and later returns to the same map, team, owner and world epoch (a world-state ABA). With short-lived offers, that would allow an old pending offer to appear current again.

V77 adds a **server-owned monotonically increasing member serial** (`direct_next_serial`) to each current game link, updated only when:
- an accepted/refused co-op Hello arrives, including opt-out/re-opt-in;
- the co-op transport stream restarts and loses its prior world Hello;
- the member *changes* map (not each packet or periodic same-map report).

The world's P2P revision now incorporates the sorted pair of these server-assigned member serials, so the reverse A/B peer view matches while old offers are invalid after leaving and returning to the same map. Missing generation always denies. On disconnect the link is forgotten and a new Hello receives a fresh serial; no persistent DB migration is necessary. Increment only at infrequent game-state transitions, not on a hot path.

## Original server regression tests

The pinned `server/tests/test_bloodborne_world.cpp`, composed with V74-V77, checks same-map A/B consent, the real A/B physical and virtual endpoints, one-sided opt-in rejection, unknown/self/duplicate link denial, map=0, same-map return yielding a **different** grant scope revision, opt-out/re-Hello yielding another **different** revision, and disconnection rejection. These are actual Qt world code compiled and linked against generated co-op protobuf, not toy-only tests.

## Still required for live P2P

- An authenticated TLS 1.3 **recipient-to-single-Qt-server** control channel and unique per-session key exporter; no prior one exists. TLS authentication must link its account to the existing game UDP session. No secrets or peer IPs on existing plaintext SHLK/WebAPI HTTP.
- A server-only grant issuer that uses this scope + freshly generated per-direction keys to build V75 sealed offers, and revokes/rechecks on every world/consent/session change.
- Client installer that verifies cryptographic grant and NAT candidate reachability before `NativeDirectSender/Receiver::Arm`; no installer exists yet. For CGNAT or opt-out relay stays unchanged.
- Confidentiality of **game UDP** separately from the V75 grant encryption: current HMAC on `SHP1` provides only packet authenticity, not encryption.
- Complete reliable GameLink ACK/sequence/retransmission migration (V73 protects current reliable frames on shadNet), two-PC game QA, and real Fornex CPU/bandwidth benchmarks.
- No game or server deployment has been performed.

The live CLS Friends service and account DB, firewall and ports on Fornex remain untouched. This code belongs to GitHub development branches only.
