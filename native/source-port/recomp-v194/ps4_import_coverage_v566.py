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


def self_test():
    ident = ('example', ('libTest', 1), ('modTest', 257))
    image = dict(symbols=[{}, dict(section=0, identity=ident),
                         dict(section=1, identity=None)],
                 relocs=[(16,7,1,0),(24,1,1,0),(32,8,0,0),(40,1,2,0)])
    expected = dict(modules={'modTest':dict(identities=1,slots=2,source_registrations=1)},
                    relocation_types={7:1,1:1},identities=1)
    assert inventory(image, {('example','libTest',1,'modTest')}) == expected
    for wrong in (('example','libTest',2,'modTest'), ('example','libTest',1,'other')):
        assert inventory(image,{wrong})['modules']['modTest']['source_registrations'] == 0
    for index in (-1,3):
        try:
            inventory(dict(image,relocs=[(16,7,index,0)]),set())
        except ValueError:
            pass
        else:
            raise AssertionError('accepted invalid symbol index')


def main():
    if sys.argv[1:] == ['--self-test']:
        self_test()
        return
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
