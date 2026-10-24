# V46: original Yharnam Together BLauncher, isolated Fornex test profile

**Development-only, opt-in IPv4 endpoint and port support. Not a public release, not Direct P2P, and not verified by two real game clients.**

The pinned launcher uses game UDP 31314, WebAPI TCP 31315, and game backend TCP 20443. Our separately isolated Fornex staging server uses UDP 32314, WebAPI 32315, and backend 21443. Production CLS on the standard ports is not modified.

To opt into testing, copy tools/SeamlessHunt-network-profile.example.json from the portable game kit to user/seamless-hunt-network.json. Change server_ipv4 to the real IPv4 address already entered as **Host IP** in the original BLauncher. The documentation-only example 198.51.100.24 is not a real service.

Only remote guests can use this file. Local host setup continues using Yharnam Together's original ports and runtime. Without the file nothing changes. A missing opt-in, invalid port, mismatched IPv4, duplicated ports, local-host override or unknown field fails closed.

Only use disposable test accounts and unique passwords. The current upstream transport is not certified end-to-end encrypted. Never reuse your CLS/GitHub password in a development realm. Crash dumps and credentials are not automatically forwarded to an alternative test WebAPI.

Only the sanitized example is included in the game kit. The actual file in user/ is player-owned and excluded from redistribution. No live account DB, gameplay assets, DNS routing, direct peer transport or public matchmaking behavior changes here.

The source edits target only bbport/launcher/bbport_coop.py and bbport/launcher/bbport_launcher_win.py, preserving the original Yharnam Together BLauncher, licenses and update channel.

Offline regression suite: python3 -m unittest discover -s tools/poc/yharnam/remote-profile-v46 -p 'test_patch_remote_ports.py' -v.
