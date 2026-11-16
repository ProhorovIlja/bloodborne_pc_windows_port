#!/usr/bin/env python3
"""Offline PS4 import inventory; optional source-registration coverage, not HLE parity.

Use tools/recomp/ps4elf.py from a trusted bloodborne-recomp checkout.
No image bytes, addresses, or NIDs are emitted.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

REG = re.compile(r'\bLIB_FUNCTION\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"'
                 r'\s*,\s*(\d+)\s*,\s*"([^"]+)"\s*,')


def inventory(image, registered):
    counts, slots, keys = Counter(), Counter(), {}
    for _, kind, index, _ in image['relocs']:
        if index == 0:
            continue
        if not 0 < index < len(image['symbols']):
            raise ValueError('relocation symbol index outside table')
        symbol = image['symbols'][index]
        if symbol['section']:
            continue
        identity = symbol['identity']
        if identity is None:
            raise ValueError('undefined relocation without an import identity')
        nid, library, module = identity
        key = nid, library[0], library[1], module[0]
        keys.setdefault(module[0], set()).add(key)
        slots[module[0]] += 1
        counts[kind] += 1
    modules = {m: dict(identities=len(v), slots=slots[m],
                       source_registrations=len(v & registered))
               for m, v in keys.items()}
    return dict(modules=modules, relocation_types=dict(counts),
                identities=sum(x['identities'] for x in modules.values()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump', type=Path)
    p.add_argument('--recomp', type=Path, required=True, help='trusted bloodborne-recomp checkout')
    p.add_argument('--registry', type=Path, action='append', default=[])
    a = p.parse_args()
    sys.path.insert(0, str((a.recomp/'tools/recomp').resolve()))
    import ps4elf
    try:
        registrations = {(n,l,int(v),m) for path in a.registry
                         for n,l,v,m in REG.findall(path.read_text(encoding='utf-8'))}
        if a.registry and not registrations:
            raise ValueError('no LIB_FUNCTION registrations found')
        print(json.dumps(inventory(ps4elf.module(a.dump), registrations), sort_keys=True))
    except (OSError, ValueError, KeyError) as e:
        p.exit(2, f'{e}\n')


if __name__ == '__main__':
    main()
