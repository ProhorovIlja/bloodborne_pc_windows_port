# Seamless Hunt × Yharnam Together: Windows one-click PoC

Player flow AFTER GitHub Actions successfully builds the package:

1. Download the GitHub Actions artifact SH-YT-Windows-OneClick-POC-20261023 (not the developer source ZIP).
2. Extract and double-click INSTALL.cmd. No Git, Python, compiler or VPN on the player's PC.
3. The installer locates the existing Yharnam Together release automatically. If needed, choose its BLauncher.exe in a Windows file picker.
4. It stages a copy under %LOCALAPPDATA%\SeamlessHunt-Yharnam-POC and launches the patched BLauncher.exe. Original client, game and saves remain untouched.
5. Inside the GUI select the Bloodborne 1.09 game folder when asked. Public Fornex IPv4 and ports are already configured: 199.195.193.131 / UDP 32314 / TCP 32315 and 21443. Afterwards double-click START.cmd.

STATUS: this is a patch of the FROZEN Windows launcher only. The playable bb-probe.exe is COPIED from an existing Yharnam Together installation; its protocol compatibility with the verified Linux server pinned to 77e350743a7cb4524cfcc1782fb6e3af64e25b15 is NOT proven. Match versions and test with isolated saves before sharing widely.

Server access should initially be restricted to testers' public IPs. The experimental backend has open registration and has NOT passed a security audit for open public access. Do not open internal TCP 32313. Production CLS is unaffected.

Windows build sources from lKaniel/bloodborne-server are GPL-2.0-or-later. No game files are distributed. To uninstall after backing up test saves, delete only the PoC folder; keep the original Yharnam Together installation.
