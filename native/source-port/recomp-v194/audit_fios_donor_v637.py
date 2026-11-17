# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline Fios2 import coverage; registration alone does not attest behavior."""
from base64 import b64encode
from hashlib import sha1, sha256
import re

SALT = bytes.fromhex('518d64a635ded8c1e6b039b1c3e55230')
NS = 'libSceFios2'


def nid(name):
    return b64encode(sha1(name.encode('ascii') + SALT).digest()[:8][::-1]).decode().rstrip('=').replace('/', '-')


def registrations(source):
    names = re.findall(r'^\s*REG\("(sceFios[A-Za-z0-9_]+)",\s*hle_fios_[A-Za-z0-9_]+\);\s*$', source, re.M)
    result = {nid(name): name for name in names}
    if not names or len(result) != len(names):
        raise ValueError('missing or ambiguous donor registrations')
    return result


def coverage(consumers, provider, donor):
    groups = {}
    for label, imports in consumers.items():
        rows = set()
        for key, sites in imports.items():
            symbol, module, library = key
            if module[0] != NS:
                continue
            if (module, library) != ((NS, 257), (NS, 1)) or not sites or any(
                    (kind, addend) != (7, 0) for _, kind, addend in sites):
                raise ValueError('unexpected Fios2 import shape')
            exports = provider.get(key, ())
            if len(exports) != 1 or next(iter(exports))[0] != 2:
                raise ValueError('missing or ambiguous Fios2 function export')
            rows.add(symbol)
        if not rows:
            raise ValueError('no Fios2 imports in ' + label)
        groups[label] = rows
    groups['combined'] = set().union(*groups.values())
    return {label: dict(total=len(rows), registered=sorted(donor[k] for k in rows & donor.keys()),
                        missing=sorted(rows - donor.keys())) for label, rows in groups.items()}


def main():
    import argparse
    import json
    from pathlib import Path
    from audit_modules_v628 import PINS, link_tables

    p = argparse.ArgumentParser(description=__doc__)
    for name in ('eboot', 'libc', 'fios2', 'bbhost_fios_cpp'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    blobs = [f.read_bytes() for f in (a.eboot, a.libc, a.fios2)]
    if tuple(sha256(blob).hexdigest() for blob in blobs) != PINS:
        p.error('unsupported eboot/PRX hash or module order')
    tables = [{}, {}, {}]
    for blob, details in zip(blobs, tables):
        link_tables(blob, details=details)
    source = a.bbhost_fios_cpp.read_bytes()
    donor = registrations(source.decode('utf-8'))
    report = coverage({name: d['imports'] for name, d in zip(('eboot', 'libc'), tables)},
                      tables[2]['exports'], donor)
    print(json.dumps(dict(donor_sha256=sha256(source).hexdigest(), coverage=report), sort_keys=True))


if __name__ == '__main__':
    main()
