# Yharnam Together 1.4.0: server-only production hardening candidate

**Status:** isolated source candidate. **NOT deployed, NOT merged, NOT certified for live players.**

This directory is an isolated experiment on a dedicated Git branch. It never changes the
Bloodborne client, the launcher, the live shadNet Docker image, DNS, Caddy, the database, or player worlds.

## What is implemented

- Upstream: [Amanises-Yharnam-Together/BBSC-Yharnam-Together](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together).
- Fixed upstream base revision: \`efa0ad265d840d9195e55db2e3216f46f7daedd0\`.
- Pinned [PR #540](https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/540) source:
  \`0b948061f8df16ceb8588e19cd858a0fffea7ddc\`.
- The preparation script checks all eight upstream changes against an exact **server/docs-only**
  allowlist. It refuses different PR contents instead of silently picking up later commits.
- The PR drops traffic above each encrypted link's existing rate limit but no longer bans the
  **entire source IP** for 15 minutes, preventing collateral disconnections behind shared NAT.
  Operator-configured bans in \`banned.txt\` remain enforced.
- Additional local regression: a second player behind the same IP keeps its link and hello
  budget after a different player floods.
- Additional local compatibility: the private \`admin stats\` JSON keeps its legacy
  \`"bans": 0\` field while adding the new \`"floods"\` field. This preserves older
  read-only operational parsers. \`bans\` previously counted temporary rate bans, not
  operator bans. The field becomes zero because automatic rate bans no longer exist.
- CI checks: admission behavior, encrypted-link regression, watchdog policy, and a
  strict no-client/no-launcher modified-files gate.
- Separate manual GitHub Actions job builds a **candidate Docker runtime image**.
  It does **not** upload, tag as production, or deploy that image.

## How CI is structured

\`.github/workflows/yharnam-server-hardening.yml\` runs the light native test job for this branch.
The full Docker build is opt-in through GitHub Actions workflow_dispatch, because
Qt 6.8 + protobuf compilation is significantly heavier.

Both jobs run from **the pinned upstream commit**, not the changing upstream main branch.
No production data or credentials are required for either job.

For reproducibility on a development machine (not the production VPS):

\`\`\`bash
python3 yharnam-server-ops/prepare_pr540.py --self-test
python3 yharnam-server-ops/prepare_pr540.py /tmp/yharnam-pr540-candidate
\`\`\`

The output directory must not exist. The script aborts on changed upstream file scope
or mismatched patch anchors.

## Promotion gates before any live change

1. All unit tests and the full runtime Docker build must pass in the isolated CI environment.
2. Verify full hosted configuration, password sign-in behavior, HTTP routes, encryption/link
   protocol version and the 1.4.0 client build fingerprint remain unchanged.
3. Run a separate disposable shadNet container with **fresh, throwaway** databases and keys.
   Test shared-IP peers, normal reconnects, flood throttling, and admin-defined bans.
4. Compare live metrics (without exposing player identifiers or link keys), ideally with
   a canary and explicit maintenance window.
5. Prepare an exact rollback to the running image SHA. **Never automatically recreate the
   live container, reinitialize databases, replace \`link_key.bin\`, or deploy on a timer.**

The source image identified during read-only V32/V33 auditing was
\`sha256:6295bc890a6e...\`, but a deployment gate must re-read its full digest.
Do **not** trust this abbreviated value as an image identity.

## Existing live evidence, 8 Nov 2026

- 20–22 players; container healthy, no restarts.
- Approx. 12.46% link-thread busy; 39.3% of one CPU core across the container.
- 179 MiB container memory, zero new UDP socket receive/send buffer errors in 60 s.
- 366 new \`bad_tags\` in 60 s (cryptographic tag failures, **not** the hosted
  rate limiter), 0 \`datagrams_dropped\` in that interval and 0 new rate bans.

This evidence does **not** show current flood activity. PR #540 addresses a known
failure mode rather than a demonstrated ongoing outage at this sample.

## Repository permissions

The connected GitHub account can **read** the upstream organization repository but
cannot push to it. This isolated branch lives in the account's writable repository
instead. Do not merge these operations-only files into the unrelated native-port
\`master\` branch without a deliberate repository decision. An upstream PR requires
a fork or upstream write permission.

## Deliberately excluded from this server-only change

- Client, launcher, mod enforcement, local game hooks and native port.
- Changes to the player protocol, world-save format, passwords or game progress.
- Automatic backups, external backups and backups retention.
- DNS/Caddy routing, production Docker Compose, credentials and user databases.

The server-only branch can evolve into further tested fixes. The current VPS and its
23-player-class live workload should remain completely untouched until promotion gates pass.
