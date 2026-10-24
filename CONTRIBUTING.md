# Contributing to Seamless Hunt

Seamless Hunt is a modified experimental **Yharnam Together** build and
community interoperability effort. Contributions must make the existing
native Windows game, its BLauncher, Qt shadNet networking or the Ubuntu 24.04
server **safer and more reliable**, not silently replace the architecture.

Before submitting a PR, please read [CREDITS.md](CREDITS.md) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## External code intake (mandatory)

Do not assume that a publicly readable GitHub repository is open source.
Every new copied code segment, file, binary, model or asset **must** have:

- **Provenance:** project, author/maintainer, exact source URL, immutable
  commit or release checksum, file paths and what is being modified.
- **Permission:** explicit license or documented permission, identified at
  the version used; all obligations and compatibility checked against
  the Yharnam Together upstream and the other included components.
- **Attribution:** original header and notices preserved; add a specific
  row to [CREDITS.md](CREDITS.md) and applicable notices to
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Record whether code
  is *actually shipped*, *indirectly inherited*, *research-only* or *idea-only*.
- **Compatibility:** Windows/MSVC/CLANG64 runtime, the source pin and
  v1.09 game edition, Linux Ubuntu 24.04 / Qt 6.8.3, co-op protocol,
  gameplay event hooks, saves and anti-desync behavior checked.
- **Measured value:** before/after performance and network diagnostics
  where applicable; no auto-enabled arbitrary cheats or patch bundles.
- **Rollback:** reversible change with tests covering bad files and version
  mismatch, and a safe way to disable the feature if it fails.

No import from closed-source mods, leaked console source, proprietary game
assets or unknown-license repositories without explicit authorization. The
user supplies their own legitimate copy of Bloodborne. A reference to a
person/project in this repository does not make them a collaborator or
endorser.

## Development structure and source hierarchy

The sole maintained codebase for new player work is
`feature/seamless-hunt-mainline`. It builds the pinned
`lKaniel/bloodborne-server` native game/launcher/Qt server via
`tools/poc/yharnam/unified-v9/compose_sources.py`.

The older repository `master` is reference material, **not** a valid
shortcut for replacing the Yharnam Together launcher or engine. New upstream
tags such as v1.2.0 must be evaluated by commit-level diff and protocol
regression tests; do not bump a pin just to claim the latest version.

## Testing and public builds

A PR must pass real Windows native game and native Qt server builds,
Ubuntu 24.04/Qt 6.8.3 server tests, archive license/contents verification,
and versioned source-contract checks. These are **necessary but not
sufficient**: NPC summons, door interactions for guests, death and revive,
password matching, long sessions, PS4/shadPS4 interoperability and global
Fornex matchmaking still need supervised, real game sessions.

Keep the existing Fornex production data and services intact. Use disposable
test ports, no live account secrets, and no automatic merge/release. Never
publish an internal GitHub Actions artifact as a validated end-user installer.

## Attribution requests

If an author asks for a correction or removal, open an issue with the
original revision and notices. Respond by preserving evidence, pausing
distribution where needed, and correcting attribution or reverting code.
No project branding should claim another contributor's endorsement.
