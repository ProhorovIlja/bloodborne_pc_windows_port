#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V320: source-locked original Windows YT launcher authority pin injection.

The trusted launcher reads a user-placed public EdDSA key from its own
private settings directory. It strips any inherited/extra_env override
of the P2P trust root before launching the game. An incoming Coop grant
NEVER supplies a trust key. Default is no key => no physical peer route.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
BLOB="e881f2c0343371323fbb51798486bf6717d31401"
REL="bbport/launcher/bbport_launcher_win.py"

def once(s:str,old:str,new:str)->str:
    if s.count(old)!=1:
        raise ValueError("original Windows launcher source drift")
    return s.replace(old,new,1)

def patched(s:str)->str:
    helper='''def shyt_authority_pin_from_config_v320():
    """Read a PUBLIC EdDSA key from the launcher's own settings, never UDP.

    The administrator/user must first verify the server key out of band
    and put its 64 hexadecimal characters in shyt-p2p-authority.pub.
    A missing/unsafe file does not turn off the ordinary server relay.
    """
    path=CONFIG_DIR / 'shyt-p2p-authority.pub'
    try:
        if path.is_symlink() or not path.is_file() or not 64<=path.stat().st_size<=66:
            return None
        data=path.read_bytes()
        if not 64<=len(data)<=66:
            return None
        value=data.decode('ascii').rstrip('\\r\\n')
        if not re.fullmatch(r'[0-9a-fA-F]{64}',value) or not any(
                char!='0' for char in value):
            return None
        return value.lower()
    except (OSError, UnicodeError, ValueError):
        return None


'''
    s=once(s,"def game_environment(s, frame_generation=None):",
           helper+"def game_environment(s, frame_generation=None):")
    return once(s,"    env['PYTHONUNBUFFERED'] = '1'","""    # V320: no inherited or Advanced extra_env key may choose the
    # peer EdDSA trust root. Only the independently verified operator
    # key in this launcher's local settings can authorize Direct P2P.
    env.pop('SHYT_P2P_AUTHORITY_PUB_HEX',None)
    trusted_pub=shyt_authority_pin_from_config_v320()
    if trusted_pub:
        env['SHYT_P2P_AUTHORITY_PUB_HEX']=trusted_pub
    env['PYTHONUNBUFFERED'] = '1'""")

def git(root:Path,*args:str)->str:
    r=subprocess.run(["git","-C",str(root),*args],
        capture_output=True,text=True,timeout=12)
    if r.returncode: raise ValueError("not pinned original YT checkout")
    return r.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument('--upstream-checkout',required=True,type=Path)
    p.add_argument('--mode',choices=('check','apply'),default='check')
    a=p.parse_args()
    root=a.upstream_checkout.resolve(strict=True)
    target=root/REL
    if (git(root,'rev-parse','HEAD')!=PIN or
        target.is_symlink() or not target.is_file() or
        git(root,'hash-object',REL)!=BLOB):
        raise ValueError("unpinned original YT launcher")
    new=patched(target.read_text(encoding='utf-8'))
    if a.mode=='apply':
        target.write_text(new,encoding='utf-8')
        print("SHYT_V320_ORIGINAL_WINDOWS_LAUNCHER_TRUSTED_PIN_DEFAULT_OFF")
    else:
        print("SHYT_V320_ORIGINAL_WINDOWS_LAUNCHER_PIN_ANCHORS_PASS")

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SystemExit('V320 rejected untrusted launcher patch: '+
                         type(exc).__name__) from None
