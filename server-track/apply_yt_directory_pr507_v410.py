#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V410 source-locked backport of original YT PR #507 HTTP-directory bug.

Pinned to original YT 1.3.1 source, no Fornex interaction or game files.
On malformed source, repeated patch or provenance mismatch: refuse.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

YT_SHA="5d2305ee611ef1e03be39ff925f0da75c9a70393"
FILE="server/directory/directory.py"
YT_BLOB="1ae7c4e859827fc89906b92acc655aaf1cb072ca"
OLD="""            said = self.headers.get('Authorization', '')
            if not token or not hmac.compare_digest(said.encode(), f'Bearer {token}'.encode()):
                return self.answer(401, {'error': 'token'})
            size = int(self.headers.get('Content-Length') or 0)
            if size > BODY_MAX:
                return self.answer(413, {'error': 'too large'})
            try:
                body = json.loads(self.rfile.read(size) or b'{}')
"""
NEW="""            # YT #507: read a bounded request before an auth denial.
            # A 401 with unread TCP input can reset the socket on Windows.
            try:
                size = int(self.headers.get('Content-Length') or 0)
            except (ValueError, TypeError, OverflowError):
                return self.answer(400, {'error': 'invalid length'})
            if size < 0:
                return self.answer(400, {'error': 'invalid length'})
            if size > BODY_MAX:
                return self.answer(413, {'error': 'too large'})
            data = self.rfile.read(size)
            said = self.headers.get('Authorization', '')
            if not token or not hmac.compare_digest(said.encode(), f'Bearer {token}'.encode()):
                return self.answer(401, {'error': 'token'})
            try:
                body = json.loads(data or b'{}')
"""

def git(root:Path,*args:str)->str:
    p=subprocess.run(["git","-C",str(root),*args],
                     capture_output=True,text=True,timeout=10)
    if p.returncode:
        raise ValueError("unverified original YT Git checkout")
    return p.stdout.strip()

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--checkout",required=True,type=Path)
    parser.add_argument("--mode",required=True,choices=("check","apply","verify-patched"))
    a=parser.parse_args()
    root=a.checkout.resolve(strict=True)
    file=root/FILE
    if file.is_symlink() or not file.is_file() or file.stat().st_size>100000:
        raise ValueError("unsafe YT directory source")
    if git(root,"rev-parse","HEAD")!=YT_SHA or \
       git(root,"rev-parse","HEAD:"+FILE)!=YT_BLOB:
        raise ValueError("YT commit/blob is not authentic pinned 1.3.1")
    original=git(root,"show","HEAD:"+FILE)
    if original.count(OLD)!=1:
        raise ValueError("unexpected original directory source")
    expected=original.replace(OLD,NEW)
    existing=file.read_text(encoding="utf-8")
    # Git-show stdout strips trailing LF, while checked-out file retains LF.
    if a.mode in ("check","apply"):
        if git(root,"hash-object",FILE)!=YT_BLOB or existing.count(OLD)!=1:
            raise ValueError("unverified or already modified YT directory")
        if a.mode=="apply":
            file.write_text(existing.replace(OLD,NEW),encoding="utf-8")
    else:
        if existing.rstrip("\n")!=expected.rstrip("\n") or existing.count(NEW)!=1:
            raise ValueError("directory patch drifted after application")
    print("SHYT_V410_PINNED_ORIGINAL_YT_PR507_HTTP_DIRECTORY_"+a.mode.upper().replace("-","_")+"_PASS")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:
        raise SystemExit("SHYT_V410_DIRECTORY_REFUSED_UNVERIFIED_SOURCE: "+str(e)) from None
