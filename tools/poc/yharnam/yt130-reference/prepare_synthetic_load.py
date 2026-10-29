#!/usr/bin/env python3
"""Source-verified fix to synthetic upstream bbload flag quoting only."""
import hashlib
from pathlib import Path
import shlex
import sys
BLOB="96d9de566428fe040947cfdf9124c380ae09e89b"
SOURCE=Path("server/loadtest/run_load.py")
FINGERPRINT="bb-build 1;version=dev;protocol=9;"
def sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
def transform(raw):
    if sha(raw)!=BLOB:
        raise ValueError("Source differs from pinned v1.3 upstream blob")
    s=raw.decode("utf-8")
    if s.count("import argparse\n")!=1 or s.count("args.extra.split()")!=1:
        raise ValueError("Exact pinned upstream syntax mismatch")
    anchor = '        "packets_received": sum(r["packets_received"] for r in results),'
    if s.count(anchor) != 1:
        raise ValueError("Pinned upstream receipt summary changed")
    s = s.replace("import argparse\n","import argparse\nimport shlex\n",1)
    s = s.replace("args.extra.split()","shlex.split(args.extra)",1)
    return s.replace(anchor, anchor + '\n' +
        '        "game_receivers": sum(r["game_receivers"] for r in results),', 1).encode()
def check_argv():
    if shlex.split("--build '"+FINGERPRINT+"'")!=["--build",FINGERPRINT]:
        raise ValueError("Bad build fingerprint command parsing")
if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: prepare_synthetic_load.py DISPOSABLE_CLONE")
    check_argv()
    f=Path(sys.argv[1]).resolve()/SOURCE
    if not f.is_file() or f.is_symlink():
        raise ValueError("Not a regular isolated upstream load script")
    f.write_bytes(transform(f.read_bytes()))
    print("SHYT_SYNTHETIC_BBLOAD_PINNED_V13_FINGERPRINT_ARGV_READY")
