#!/usr/bin/env python3
"""Reproducible SERVER-ONLY shadNet PR #540 candidate, never touches production.

The upstream source and the PR head are pinned by full commit SHA.
The two tiny local overlays preserve the legacy stats key and cover shared NAT.
"""
import argparse
from pathlib import Path
import subprocess
import sys

UPSTREAM = "https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together.git"
BASE = "efa0ad265d840d9195e55db2e3216f46f7daedd0"
HEAD = "0b948061f8df16ceb8588e19cd858a0fffea7ddc"
ALLOWED = {
    "docs/HOSTED_SERVER.md",
    "server/src/admin.cpp",
    "server/src/admission.cpp",
    "server/src/admission.h",
    "server/src/link_server.cpp",
    "server/src/link_server.h",
    "server/tests/test_admin.cpp",
    "server/tests/test_admission.cpp",
}

STATS_OLD = '                        {"floods", static_cast<qint64>(count.floods)}},'
STATS_NEW = ('                        {"floods", static_cast<qint64>(count.floods)},\n'
             '                        {"bans", static_cast<qint64>(0)}},')
ADMIN_TEST_OLD = '  CHECK(stats.contains("hellos_refused") && stats.contains("floods"));'
ADMIN_TEST_NEW = ('  CHECK(stats.contains("hellos_refused") && stats.contains("floods") &&\n'
                  '        stats.contains("bans") && stats["bans"].toInt() == 0);')
NAT_ANCHOR = 'int ABigLinkWithinItsRateIsFine() {'
NAT_CASE = r'''// One misbehaving peer must never ban another peer sharing a home/CGNAT IP.
int ANoisyPeerDoesNotBanItsNatNeighbour() {
  Limits limits;
  limits.datagrams_per_second = 2;
  limits.datagram_burst = 2;
  limits.strikes_to_ban = 2;
  Guard guard{limits};
  for (int second = 0; second <= 2; ++second) {
    const qint64 at = second * 1000;
    for (int i = 0; i < 40; ++i) {
      guard.AllowDatagram(1, Home, 100, at);
    }
  }
  CHECK(guard.Count().floods >= 1);
  CHECK(!guard.Banned(Home));
  CHECK(guard.AllowDatagram(2, Home, 100, 3000));
  CHECK(guard.AllowHello(Home, 3000));
  CHECK(guard.TakeFloods().size() >= 1);
  return 0;
}

'''
NAT_CALL_OLD = '  failed |= AFloodingLinkIsDroppedAndReportedNeverBanned();'
NAT_CALL_NEW = NAT_CALL_OLD + '\n  failed |= ANoisyPeerDoesNotBanItsNatNeighbour();'


def replace_exact(text, old, new, path):
    if text.count(old) != 1:
        raise RuntimeError(f"unexpected upstream contents: {path}: {text.count(old)} anchors")
    return text.replace(old, new, 1)


def patch_file(root, relative, old, new):
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"missing or unsafe upstream file: {relative}")
    before = path.read_text(encoding="utf-8")
    after = replace_exact(before, old, new, relative)
    path.write_text(after, encoding="utf-8")


def run(*args):
    subprocess.run(args, check=True, timeout=480, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE, text=True)


def output(*args):
    result = subprocess.run(args, check=True, timeout=120, capture_output=True, text=True)
    return result.stdout.strip()


def prepare(destination):
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("destination must not exist, to prevent accidental overwrites")
    destination.parent.mkdir(parents=True, exist_ok=True)
    run("git", "init", "-q", str(destination))
    run("git", "-C", str(destination), "remote", "add", "origin", UPSTREAM)
    for revision in (BASE, HEAD):
        run("git", "-C", str(destination), "fetch", "--no-tags", "--depth=1", "origin", revision)
    changed = set(output("git", "-C", str(destination), "diff", "--name-only", BASE, HEAD).splitlines())
    if changed != ALLOWED:
        raise RuntimeError("PR #540 changed-file scope drift: " +
                           repr(sorted(changed ^ ALLOWED)))
    run("git", "-C", str(destination), "checkout", "-q", "--detach", HEAD)
    patch_file(destination, "server/src/admin.cpp", STATS_OLD, STATS_NEW)
    patch_file(destination, "server/tests/test_admin.cpp", ADMIN_TEST_OLD, ADMIN_TEST_NEW)
    patch_file(destination, "server/tests/test_admission.cpp", NAT_ANCHOR, NAT_CASE + NAT_ANCHOR)
    patch_file(destination, "server/tests/test_admission.cpp", NAT_CALL_OLD, NAT_CALL_NEW)
    if output("git", "-C", str(destination), "rev-parse", "HEAD") != HEAD:
        raise RuntimeError("source revision mismatch")
    modified = set(output("git", "-C", str(destination), "diff", "--name-only").splitlines())
    if modified != {"server/src/admin.cpp", "server/tests/test_admin.cpp",
                    "server/tests/test_admission.cpp"}:
        raise RuntimeError("unexpected overlay modifications")
    print("CANDIDATE_READY source_pin=" + HEAD +
          " pr=540 client_files=UNCHANGED launcher_files=UNCHANGED deploy=NO")


def self_test():
    assert replace_exact("a b", "a", "A", "fixture") == "A b"
    try:
        replace_exact("a b", "x", "y", "fixture")
    except RuntimeError:
        pass
    else:
        raise AssertionError("missing anchor accepted")
    assert "server/src/admission.cpp" in ALLOWED and len(ALLOWED) == 8
    assert all(p.startswith(("server/", "docs/")) for p in ALLOWED)
    assert "ANoisyPeerDoesNotBanItsNatNeighbour" in NAT_CASE
    assert '"bans"' in STATS_NEW and '"floods"' in STATS_NEW
    print("SELF_TEST_PASS anchored_overlays,server_only_allowlist,nat_regression")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", nargs="?", help="new empty directory for upstream checkout")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.destination:
        parser.error("destination is required")
    prepare(Path(args.destination).resolve(strict=False))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"CANDIDATE_FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
