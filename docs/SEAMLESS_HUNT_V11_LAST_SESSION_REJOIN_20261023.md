# Seamless Hunt V11: last active hunt reconnect
Date: 2026-10-23. Development-only, not a player release.

Requested modes in the existing Bloodborne Team menu: Off, Ask (default), Auto. A setting must affect **return to a prior hunt on title-screen character load only**. In-game transport drop/reconnect continues automatically, regardless of mode.

Pinned upstream: lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15.
The actual upstream server currently remembers team membership while one member is signed in and transmits TeamStart/TeamSession; previous behavior can return a user to an active hunt. Persisting the last *world* alone does not prove the last online team remains valid.

New native header: tools/poc/yharnam/last-session-v11/last_session_policy.hpp.
It saves per-character reconnect anchors (account member, team id, party, world, protocol, save slot, expiry), and preference Off/Ask/Auto; no credentials, remote IPs or secrets. Auto is allowed only for server-reported authenticated active membership, matching team/world/build/slot/protocol, with an anchor less than 24h old. It never selects another session just because it is the most recent lobby.

Tested locally: C++20 Release CTest 1/1 passed; native source patcher Python unittest 3/3 passed. Ten pinned real upstream patch anchors independently located exactly once.

A developer-only archive SH-YT-LAST-SESSION-V11-20261023.zip includes patch_native_resume.py to patch the native overlay, game bridge and title gate after V9. Full Windows native runtime and Qt server were NOT built, and V11 is NOT YET included in the automatic V9 composer/CI. Do not deploy this on Fornex or CLS.

Open correctness concerns before production: actual TeamStart must not be accepted until server reconfirms team identity and character mapping; Ask needs a prominent manual Start/Resume UI path; the implementation must confirm saved file and game protocol lifetime, title loading timeout, race-free preference storage, and explicit disconnect/leave suppression. Server must expose stable session identity/epoch and membership, ideally separate from its in-memory team or old world ID. Password/private room rejoin still requires server authorization; stale membership must never bypass access rules.

Project Drive: https://drive.google.com/drive/folders/1_Yjz9ysS5mhL0mXUEoRqz0u3bjK6sIxM .
