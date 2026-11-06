#!/usr/bin/env python3
"""Read-only, count/booleans-only verification of pinned public bbrecomp API v4.

This doesn't build/recompile copyrighted Bloodborne code. It rejects unknown
changes to a vendor ABI before we try a Windows DLL integration. Upstream's
current full library builder is macOS arm64 only, even if this smoke test passes.
"""
import argparse
import json
from pathlib import Path
import re

PIN = '8f31ec7c41f252730c6325d52647046baef7549f'
EXPECTED = {'RcApi': (
    'uint32_t version;', 'uint64_t image_base;',
    'uint64_t (*step)(BbCpu *cpu);',
    'void (*call)(BbCpu *cpu, uint64_t target, uint64_t next);',
    'void (*tail)(BbCpu *cpu);',
    'void (*bail)(BbCpu *cpu, uint64_t entry_rsp);',
    'void (*trace)(uint64_t offset, const uint64_t r[16], const BbCpu *cpu);'
), 'RcFunction': (
    'uint64_t offset, size, hash;', 'RcFn fn;', 'RcFn *direct;'
)}

def fields(text, name):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    m = re.search(r'typedef\s+struct\s*\{([^{}]*)\}\s*' + re.escape(name) + r'\s*;', text, re.S)
    if m is None:
        raise ValueError('missing struct '+name)
    # Split semicolon terminators, never split commas inside declarations.
    return tuple(re.sub(r'\s+', ' ', field).strip()+';'
                 for field in m.group(1).split(';') if field.strip())

def audit(upstream, local):
    up, loc = str(upstream), str(local)
    results = {}
    for name, expected in EXPECTED.items():
        if fields(up, name) != expected or fields(loc, name) != expected:
            raise ValueError('ABI '+name+' no longer matches pinned public source')
        results[name] = True
    regexes = (
        r'#define\s+BB_RECOMP_API_VERSION\s+4u\b',
        r'typedef\s+const RcFunction\s*\*\s*\(\*RcInit\)\s*\(const RcApi \*api, size_t \*count\)\s*;'
    )
    for pattern in regexes:
        if not re.search(pattern, up) or not re.search(pattern, loc):
            raise ValueError('recompiled module version/initialization API drift')
    return results

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream-root', type=Path, required=True)
    parser.add_argument('--project-header', type=Path, required=True)
    a=parser.parse_args(argv)
    public = a.upstream_root / 'src/recomp/rc.h'
    builder = a.upstream_root / 'tools/recomp/build_library.py'
    for file in (public,builder,a.project_header):
        if not file.is_file() or file.is_symlink() or file.stat().st_size > 256_000:
            raise ValueError('missing or unbounded expected source file')
    result = audit(public.read_text(encoding='utf-8'), a.project_header.read_text(encoding='utf-8'))
    build = builder.read_text(encoding='utf-8')
    # Exact blocker: app's shipping generator/linker still target Mach-O ARM64.
    windows_builder_complete = not ('--target=arm64-apple-macos15' in build or 'ld64.lld' in build)
    print(json.dumps({'upstream_recomp_api':4,'ABI_structs_verified':result,
        'synthetic_win64_dll_abi_only':True,
        'upstream_windows_x64_game_library_builder_ready':windows_builder_complete,
        'actual_bloodborne_game_recompiled_or_booted':False}, separators=(',',':')))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
