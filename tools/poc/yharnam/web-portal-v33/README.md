# V33 read-only Hunter Portal

This package is a **staged public snapshot projector and standalone web
landing page**, NOT a live Bloodborne location feed or a deployed account
service. It does not run against CLS/Fornex or other people's servers.

- `presence.py`: O(n) bounded projection of verified game server link
  observations, max 4096 live peers, stale TTL, explicit heartbeat and
  **unavailable ≠ zero online**. Public display never includes account IDs,
  IPs, precise position, PvP markers or session secrets.
- `site/index.html`: dark accessible mobile-responsive landing page,
  GitHub releases download link, install and auto-update roadmap, real API
  fetch from **same origin only**, and a deliberately truthful "not
  connected" empty state. No hard-coded fictional player counts.
- `test_presence.py`: unknown-vs-zero, opt-in, area-count
  suppression under three, PvP privacy, invalid inputs, stale events,
  bounded memory, server heartbeat and departure.

To become a REAL live map:
1. Source observations from a trusted, running link-server session table;
   never accept a client-supplied account/IP or location as authoritative.
2. Place a private, authenticated ingestion adapter next to the server,
   authenticated to the internal HTTP service. The public website must not
   have direct database access or allow untrusted event submission.
3. Return the public projection from a same-origin HTTP endpoint
   `GET /api/public/v1/presence`. Set caching to <=5s, rate limit public
   requests, and treat unavailable/stale as unavailable rather than zero.
4. Only publish area-level populations for consenting hunters. Suppress
   populations below 3 and all PvP-active individual locations. Add
   team-only authenticated detailed positions in a separate endpoint after
   authorization/party membership checks, never mixed with public data.
5. An actual **map geometry asset** must be versioned and licensed from
   compatible open sources or derived from owned game data client-side.
   Do not invent map coordinates or copy The Hunter's Dream map art.
6. Audit retention, consent, privacy and resource usage. Site should fall
   back to a non-moving static install guide when game data is absent.

No game assets, installer or password collection included.
