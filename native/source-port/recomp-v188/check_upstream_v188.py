#!/usr/bin/env python3
"""Bounded, read-only verifier for the pinned public generator contract."""
import argparse
import json
from pathlib import Path
import re

PIN = '8f31ec7c41f252730c6325d52647046baef7549f'

def guard(root):
    files = {'emitter': root/'tools/recomp/bbrecomp.c',
             'builder': root/'tools/recomp/build_library.py',
             'api': root/'src/recomp/rc.h'}
    contents = {}
    for name, p in files.items():
        if p.is_symlink() or not p.is_file() or not 64 < p.stat().st_size < 2_000_000:
            raise ValueError('pinned public generator source missing or oversized')
        contents[name] = p.read_text(encoding='utf-8')
    emitter = contents['emitter']
    builder = contents['builder']
    api = contents['api']
    if 'bb_recomp_init(const RcApi *api, size_t *count)' not in emitter:
        raise ValueError('public recompiler initialization emitter drift')
    if 'visibility(' not in emitter or 'RcFunction' not in emitter:
        raise ValueError('original generated table no longer uses reviewed visibility/layout')
    if not re.search(r'#define\s+BB_RECOMP_API_VERSION\s+4u\b', api):
        raise ValueError('upstream recompiler ABI changed')
    if ('--target=arm64-apple-macos15' not in builder
            or 'ld64.lld' not in builder):
        raise ValueError('upstream build profile has changed: re-audit real Windows support')
    return {'pinned_recompiler_source_checked':True,
            'win64_pe_coff_linker_adapter_needed':True,
            'upstream_default_game_library_builder_is_macos_arm64':True,
            'game_code_generated_or_built_in_ci':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--upstream-root',type=Path,required=True)
    args=p.parse_args()
    try: report=guard(args.upstream_root)
    except (OSError,ValueError):
        print(json.dumps({'pinned_recompiler_source_checked':False}))
        return 2
    print(json.dumps(report,separators=(',',':')))
    return 0
if __name__=='__main__':raise SystemExit(main())
