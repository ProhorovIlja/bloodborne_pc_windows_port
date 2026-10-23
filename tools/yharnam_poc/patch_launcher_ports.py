#!/usr/bin/env python3
"""Patch source-only Yharnam Together launcher for isolated staging port selection.

The installed BLauncher.exe will NOT be altered. Rebuild from a checkout after patching.
Options are opt-in via environment variables set only on the developer TEST client.
"""
import argparse
import hashlib
from pathlib import Path

PIN='77e350743a7cb4524cfcc1782fb6e3af64e25b15'
SOURCE_LINE='SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = 31313, 31315, 31314, 20443'
PATCH_LINE='SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = (\\n'
PROD=(31313,31315,31314,20443)
PATCH='''# Seamless Hunt isolated dedicated-server PoC. Default (no environment overrides)
# remains EXACTLY upstream behavior; never activate in a production package.
def _sh_poc_port(key, default):
    raw = os.environ.get(key, '').strip()
    if not raw:
        return default
    try:
        result = int(raw, 10)
    except ValueError as error:
        raise ValueError('Invalid staging port in ' + key) from error
    if not 1024 <= result <= 65535:
        raise ValueError('Out-of-range staging port in ' + key)
    return result

SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = (
    _sh_poc_port('SH_YT_TCP_PORT', 31313),
    _sh_poc_port('SH_YT_WEBAPI_PORT', 31315),
    _sh_poc_port('SH_YT_UDP_PORT', 31314),
    _sh_poc_port('SH_YT_BACKEND_PORT', 20443),
)
'''

def patch_content(source):
    if PATCH_LINE in source and '_sh_poc_port' in source:
        return source,False
    if source.count(SOURCE_LINE)!=1:
        raise ValueError('Unexpected upstream launcher revision: port line not uniquely found')
    if '\\nimport os\\n' not in source and not source.startswith('import os\\n'):
        raise ValueError('Missing expected os import in upstream launcher')
    return source.replace(SOURCE_LINE,PATCH,1),True

def patch_file(path:Path):
    content=path.read_text(encoding='utf-8')
    result,changed=patch_content(content)
    if changed:
        backup=path.with_suffix('.py.shpoc-orig')
        if backup.exists():
            raise FileExistsError(f'Backup already exists: {backup}')
        backup.write_bytes(path.read_bytes())
        path.write_text(result,encoding='utf-8')
        print('PATCHED',path,'; ORIGINAL BACKUP:',backup)
    else:
        print('UNCHANGED: PoC port override already installed')
    return changed

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkout',type=Path,required=True)
    ap.add_argument('--restore',action='store_true')
    args=ap.parse_args()
    path=args.checkout/'bbport'/'launcher'/'bbport_coop.py'
    if not path.is_file():
        ap.error('Missing Yharnam Together bbport_coop.py in source checkout')
    backup=path.with_suffix('.py.shpoc-orig')
    if args.restore:
        if not backup.is_file():ap.error('No saved original to restore')
        if '_sh_poc_port' not in path.read_text(encoding='utf-8'):
            ap.error('Current file is not the staging patch. Refusing to overwrite edits.')
        path.write_bytes(backup.read_bytes())
        backup.unlink()
        print('RESTORED original source')
    else:
        patch_file(path)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
