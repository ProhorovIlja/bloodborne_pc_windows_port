# Native V198: private incremental Win64 AOT build, no runtime EBOOT

**Goal:** take the original public `bloodborne-native/bloodborne-recomp`
full-function C output (`recomp.c` + potentially hundreds of
`recomp_<image_window>.c` shards) and turn it into separate **true AMD64
Windows COFF object modules**. Reuse objects whose C, header, compiler
version, flags and source pin are unchanged. No PS4 ELF loader is used by
the resulting game-code object files.

## Implemented

`build_incremental_coff_v198.py` is a reusable private Windows-side
compiler driver. Source-locks the complete upstream
`8f31ec7c41f252730c6325d52647046baef7549f` CPU/compiler ABI,
checks the V195 Win32-native generated-code helper, and requires real
Zydis headers.

- Reads only previously generated original C; does **not** parse
  `eboot.bin` or compile code at game runtime.
- Uses actual Windows `clang-cl` with 64-bit native COFF `.obj` outputs
  and checks the `0x8664` machine header, rather than merely naming
  an ELF object `.obj`.
- Independently compiles each original C shard (up to eight parallel
  compiler processes), writes to temporary files and atomically installs
  each completed object.
- Fingerprints source SHA-256, full Win64 compiler command, compiler
  version, pinned upstream commit, original CPU/RC headers and real
  Zydis version before reuse. An unchanged source is not rebuilt on
  subsequent calls; changing one shard rebuilds only that shard.
- Records a deterministic, resumable `native-coff-v198.json` in the
  **private** object directory; neither hashes nor generated C are
  automatically sent to GitHub.
- Optionally links a deliberately separate, source-only **synthetic**
  native entrypoint into a real Windows PE executable for CI. The host
  is NOT the retail game; production requires a complete independent
  engine, imports, Windows graphics/audio/IO and original code.
- Refuses game-derived output inside any Git worktree; callers must
  use a private, local directory outside the repository. No raw game
  source, player data or game binaries are uploaded by this build.

## CI evidence

`.github/workflows/native-v198-incremental-coff.yml` regenerates five
invented **whole** x86-64 functions using the pinned original
`bbrecomp.c` with genuine Zydis, compiles the **same** original generated
`recomp*.c` shards into true AMD64 COFF objects on Windows Server 2022,
links and runs a private-independent Windows PE entrypoint, checks
inter-function `CALL` and `RET`, then repeats compilation to verify
zero unchanged shards recompiled and one changed shard rebuilt.

**Both Linux and Windows jobs SUCCESS**, including real native Windows PE launch, incremental zero-rebuild and one-shard invalidation:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41253580155

- Original Linux generator with Zydis: SUCCESS.
- Native Windows clang-cl separately built 2 original-generator C files into
  2 checked AMD64 `.obj` files, linked them with the synthetic host and
  executed direct CALL/RET: SUCCESS.
- Second compile on identical inputs: `compiled=0, reused=2`.
- Changed one private, synthetically-generated C shard: `compiled=1, reused=1`.
- Runtime EBOOT argument refused. No full Bloodborne 1.09 executable present.

Proof is only for synthetic five whole-function C, **not the real game**.

## Private original Bloodborne ingestion blocker

On **1 November 2026**, verified the connected private Drive's
Bloodborne game root and child folder: `sce_module`, `sce_sys`
and `dvdroot_ps4` with game assets are present. A Drive metadata
search `name contains 'eboot'` returned **zero files** and the
game root has no `eboot.bin`. This is insufficient for real
full-game code scanning/recompilation. It does **not** mean game assets
are missing. We have not recompiled the entire actual 1.09 binary
through V198 and will not claim otherwise.

When a **user-owned, decrypted Bloodborne 1.09** executable is
available in a separate private location, run the pinned original
offline scripts **privately**:

1. `tools/recomp/ps4elf.py` converts the original PS4 SELF/ELF
   into the offline compiler's input image.
2. `tools/recomp/pointers.py`, real `scan`, and
   `tools/recomp/imports.py` generate the actual function
   boundaries, guest relocation pointers and import names.
3. Original `bbrecomp` generates full function C shards from that
   offline image and the full function list.
4. On Windows, `build_incremental_coff_v198.py` compiles each
   real C shard to a private native AMD64 object and resumes after
   failures. Source code, objects, hashes and executable image
   stay in a private directory. The eventual game's executable
   must **not** read `eboot.bin` or any guest PS4 executable
   at startup.

This compiler is not the whole game. Remaining blocking work:
native Windows engine startup; PS4 library/import replacements;
indirect calls, generated fallbacks and exceptions; threads/TLS/
vector instructions; native renderer based on engine-level state,
asset streaming, audio/input/media/save systems; full game/DLC/
chalices and live hardware tests. Preserve compatibility with
user-owned assets and avoid distributing copyrighted game code.

This research stays in Draft PR #84. No Fornex, YT server, merge,
original game upload or production release was performed.
