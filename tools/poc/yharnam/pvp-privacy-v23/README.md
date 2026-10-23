# V23: Competitive co-op and invasion visibility policy (staged only)

**Status:** portable role-visibility policy and test suite, NOT connected to the live game or protocol yet. The pinned protocol 7 and our composed protocol 8 do not carry authenticated faction/hostility roles or safe sighting proofs. It is unsafe to pretend they do.

User experience:
- Hunters/cooperators see their own side in party HUD, compass, map and ally HP bars.
- Multiple invaders see each other as teammates.
- Opponents do not appear on the global party HUD, map or compass with real-time exact coordinates; even when spotted they do not receive those privileged data feeds.
- Optionally, a **server-verified** sighting may generate an approximate short-lived "last seen" marker lasting <=1.5s; never exact coordinates. When server has no geometry/line-of-sight validation, no sighting may be issued.
- Enemy players remain rendered according to the game's ordinary combat visibility and network actor replication; these are **not** implemented by this policy alone. Overhead nameplates should be line-of-sight gated. Dead/spectator free camera is restricted in PvP to avoid ghosting.
- Invasions must not be allowed between incompatible old/new clients that could leak visibility metadata. Protocol negotiation must be explicit and fail closed while still supporting legacy PvE co-op separately.

Security implementation prerequisites:
1. Server-authoritative faction and side membership tied to a game session token, not a self-reported role.
2. Filter private party metadata **before serialization and transmission**; a client-only UI hide can be bypassed.
3. Separate movement replication from party HUD reports. Gameplay actor data must use appropriate server map/PVS/LoS checks to avoid wallhacks, not just client claims.
4. Snapshot/reconnect/migration and spectator code must apply the same privacy filter.
5. Test at least two invaders versus a hunting group, lag, map transitions, spectator/death, cheating clients, and protocol 7/8 fallbacks.

`sh_pvp_privacy.hpp` is O(1), no allocations, and defaults to deny when faction metadata cannot be verified. The executable test checks six role/session combinations and hostile metadata leaks. No production server or crossplay PS4 client is modified.

The full server-side privacy routing is future work and is NOT claimed completed. This is a guardrail and tested interface, not an anti-wallhack release.
