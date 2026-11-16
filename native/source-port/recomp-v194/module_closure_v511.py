# SPDX-License-Identifier: GPL-2.0-or-later
"""Inventory original bundled-module dependencies using an offline ps4elf reader."""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import struct


def key(symbol):
    if symbol['identity'] is None or symbol['type'] not in (1, 2):
        return None
    return (*symbol['identity'], symbol['type'])


def compare(images):
    """Count exact scoped identity/type matches, not successful ABI bindings."""
    exports = defaultdict(set)
    for name, image in images.items():
        for symbol in image['symbols']:
            k = key(symbol)
            if k is not None and symbol['section'] and symbol['binding'] in (1, 2):
                exports[k].add(name)
    report = {}
    for name, image in images.items():
        required = Counter()
        seen = set()
        unsupported = Counter()
        for slot, kind, index, _ in image['relocs']:
            if slot in seen or not 0 <= index < len(image['symbols']):
                raise ValueError('invalid relocation metadata')
            seen.add(slot)
            if index and not image['symbols'][index]['section']:
                k = key(image['symbols'][index])
                if k is None or kind not in (1, 6, 7) or (kind == 7 and k[-1] != 2):
                    unsupported[f'{kind}/{image["symbols"][index]["type"]}'] += 1
                    continue
                required[k] += 1
        groups = defaultdict(Counter)
        for k, slots in required.items():
            providers = exports[k] - {name}
            bucket = ('module:' + next(iter(providers)) if len(providers) == 1
                      else 'ambiguous' if providers else 'outside_supplied_modules')
            groups[bucket].update(keys=1, slots=slots, objects=int(k[-1] == 1))
        report[name] = {
            'matches': {k: dict(v) for k, v in sorted(groups.items())},
            'unsupported_slots_by_reloc_and_type': dict(sorted(unsupported.items())),
        }
    return {'images': report, 'runtime_verified': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ps4elf', required=True, type=Path,
                   help='trusted local tools/recomp/ps4elf.py from bloodborne-recomp')
    p.add_argument('--eboot', required=True, type=Path)
    p.add_argument('--libc', required=True, type=Path)
    p.add_argument('--fios2', required=True, type=Path)
    a = p.parse_args()
    try:
        spec = importlib.util.spec_from_file_location('bb_ps4elf_v511', a.ps4elf)
        if spec is None or spec.loader is None:
            raise ValueError('invalid reader path')
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        paths = {'eboot': a.eboot, 'libc': a.libc, 'fios2': a.fios2}
        if any(x.is_symlink() or not x.is_file() or not 64 <= x.stat().st_size <= 512 << 20
               for x in paths.values()):
            raise ValueError('invalid image path')
        result = compare({k: reader.module(v) for k, v in paths.items()})
    except (OSError, ValueError, KeyError, IndexError, StopIteration, struct.error):
        p.exit(2, 'V511 refused: unsupported image, reader or relocation metadata\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
