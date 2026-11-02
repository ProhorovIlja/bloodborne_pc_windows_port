#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V320: test real patched Windows launcher authority-pin reader, no imports/UI."""
from __future__ import annotations
import argparse
import ast
from pathlib import Path
import re
import tempfile

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--patched-launcher',required=True,type=Path)
    args=ap.parse_args()
    source=args.patched_launcher.read_text(encoding='utf-8')
    tree=ast.parse(source)
    functions={node.name:node for node in tree.body
               if isinstance(node,ast.FunctionDef)}
    helper=functions.get('shyt_authority_pin_from_config_v320')
    game=functions.get('game_environment')
    if not helper or not game:
        raise AssertionError('source-locked Windows launcher integration missing')
    # The inherited/advanced-env keys are unsafe as a trust root.
    # The local operator pin MUST override the completed user extra_env.
    game_src=ast.get_source_segment(source,game)
    assert game_src and game_src.index("for item in str(s['extra_env']).split():") < (
        game_src.index("env.pop('SHYT_P2P_AUTHORITY_PUB_HEX',None)"))
    assert game_src.index("env.pop('SHYT_P2P_AUTHORITY_PUB_HEX',None)") < (
        game_src.index("env['SHYT_P2P_AUTHORITY_PUB_HEX']=trusted_pub"))
    with tempfile.TemporaryDirectory() as d:
        home=Path(d)
        context={'CONFIG_DIR':home,'re':re}
        isolated=ast.fix_missing_locations(ast.Module(
            body=[helper],type_ignores=[]))
        exec(compile(isolated,'yt-test-pin','exec'),context)
        read_pin=context['shyt_authority_pin_from_config_v320']
        f=home/'shyt-p2p-authority.pub'
        assert read_pin() is None
        candidate='0123456789aBcDeF'*4
        f.write_bytes(candidate.encode('ascii')+b'\\r\\n')
        assert read_pin()==candidate.lower()
        f.write_text('0'*64,encoding='ascii')
        assert read_pin() is None
        f.write_text('Z'+candidate[1:],encoding='ascii')
        assert read_pin() is None
        f.write_bytes(candidate.encode('ascii')+b' '+b'\\n')
        assert read_pin() is None
        f.write_bytes(candidate.encode('ascii')+b'X'*100)
        assert read_pin() is None
        f.write_bytes(b'\\xff'*64)
        assert read_pin() is None
        f.unlink()
        if hasattr(f,'symlink_to'):
            other=home/'accepted'
            other.write_text(candidate,encoding='ascii')
            f.symlink_to(other)
            assert read_pin() is None
    print('SHYT_V320_REAL_WINDOWS_LAUNCHER_LOCAL_AUTHORITY_PIN_PASS')

if __name__=='__main__':
    main()
