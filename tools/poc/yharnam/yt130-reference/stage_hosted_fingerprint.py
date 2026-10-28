#!/usr/bin/env python3
"""Source-exact fix to original Hosted run_shards.py bbload build-token parser.

The compiled native server rejects bbload default build "bbload" under
CheckServerBuild. Unlike run_load.py previously patched for quoted tokens,
original run_shards.py uses args.extra.split() and breaks the required
"bb-build 1;version=dev;protocol=9;" fingerprint at whitespace. Patch ONLY
the disposable original load generator. Never weaken server build check.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shlex
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOB = "9a8e6a1dd866f9ef996ed544e3b781953e154230"
FILE = "server/loadtest/run_shards.py"
BUILD = "bb-build 1;version=dev;protocol=9;"

def git_blob(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() +
                        b"\0" + content).hexdigest()

def rewrite(data: bytes) -> bytes:
    if git_blob(data) != BLOB:
        raise ValueError("Pinned original Hosted generator blob SHA changed")
    source = data.decode("utf-8")
    if (source.count("import argparse\n") != 1 or
        source.count("args.extra.split()") != 1):
        raise ValueError("Original Hosted sharded generator anchors changed")
    source = source.replace("import argparse\n", "import argparse\nimport shlex\n", 1)
    source = source.replace("args.extra.split()", "shlex.split(args.extra)", 1)
    return source.encode("utf-8")

def verify():
    argv = shlex.split("--build '" + BUILD + "' --owner-fps 30 --follower-fps 8")
    if argv != ["--build", BUILD, "--owner-fps", "30",
                "--follower-fps", "8"]:
        raise ValueError("Hosted fixture loses original required build fingerprint")
    if "--build '" + BUILD + "'".split() == ["--build", BUILD]:
        raise ValueError("Regression: raw split unexpectedly works on build token")

def stage(root: Path):
    root = root.resolve()
    if subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                               text=True).strip() != PIN:
        raise ValueError("Must use original exact YT1.3 disposable checkout")
    p = root / FILE
    if p.is_symlink() or not p.is_file():
        raise ValueError("Original generator is missing or symlinked")
    verify()
    p.write_bytes(rewrite(p.read_bytes()))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_HOSTED_SHARD_BBLOAD_PINNED_BUILD_FINGERPRINT_PRESERVED")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_hosted_fingerprint.py PINNED_DISPOSABLE_CLONE")
    stage(Path(sys.argv[1]))
