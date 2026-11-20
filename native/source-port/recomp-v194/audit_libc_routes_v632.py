#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline V631 coverage using its compiled route probe and pinned V628 inputs."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def read_routes(text):
    routes = set()
    for line in text.splitlines():
        nid, mod, mv, lib, lv = line.split('\t')
        key = nid, (mod, int(mv)), (lib, int(lv))
        if key in routes:
            raise ValueError('duplicate provider identity')
        routes.add(key)
    if not routes:
        raise ValueError('empty provider inventory')
    return routes


def coverage(images, routes):
    game, libc, fios = images
    uses = game.get('imports', {})
    exports = libc.get('exports', {})
    for key in routes:
        definitions = exports.get(key, ())
        if len(definitions) != 1 or next(iter(definitions))[0] != 2:
            raise ValueError('provider identity has no unique libc function export')
        if key not in uses:
            raise ValueError('provider identity is not imported by the game')
        if key in fios.get('exports', {}):
            raise ValueError('provider identity also exported by Fios2')
    result = {}
    for name, image in (('eboot', game), ('fios2', fios)):
        classes = Counter()
        kinds = Counter()
        for key, sites in image.get('imports', {}).items():
            definitions = exports.get(key, ())
            if not definitions:
                continue
            if len(definitions) != 1:
                raise ValueError('ambiguous libc export')
            kind, _, _ = next(iter(definitions))
            if key in routes:
                label = 'route_candidate'
            else:
                label = {1: 'uncovered_object', 2: 'uncovered_function'}.get(kind, 'uncovered_other')
            classes[label] += 1
            for _, relocation, addend in sites:
                kinds[f'{label}:{relocation}'] += 1
                if key in routes and addend:
                    kinds['route_candidate:nonzero_addend'] += 1
        result[name] = {'identities': dict(classes), 'sites': dict(kinds)}
    return result


def main():
    from audit_modules_v628 import PINS, link_tables
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('probe', 'eboot', 'libc', 'fios2'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    blobs = [p.read_bytes() for p in (args.eboot, args.libc, args.fios2)]
    if tuple(sha256(blob).hexdigest() for blob in blobs) != PINS:
        parser.error('unsupported eboot/PRX hash or module order')
    routes = read_routes(subprocess.check_output([str(args.probe.resolve())], text=True))
    images = [{}, {}, {}]
    for blob, image in zip(blobs, images):
        link_tables(blob, details=image)
    print(json.dumps(coverage(images, routes), sort_keys=True))


if __name__ == '__main__':
    main()
