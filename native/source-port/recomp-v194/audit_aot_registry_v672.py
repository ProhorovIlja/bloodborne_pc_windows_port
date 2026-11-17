# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit startup roots against bloodborne-recomp's local generated RcFunction table."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from audit_startup_roots_v671 import audit

ROW = re.compile(r'\{0x([0-9a-f]+), ([1-9][0-9]*), 0x[0-9a-f]+ull, f_([0-9a-f]+), &d_([0-9a-f]+)\},')
START = 'static const RcFunction table[] = {'


def registrations(source):
    if source.count(START) != 1:
        raise ValueError('expected one generated RcFunction table')
    _, tail = source.split(START, 1)
    rows, end, _ = tail.partition('\n};')
    if not end:
        raise ValueError('unterminated generated table')
    entries = set()
    for line in rows.splitlines():
        if not line.strip():
            continue
        row = ROW.fullmatch(line.strip())
        if not row:
            raise ValueError('unsupported generated RcFunction row')
        addr, _, fn, dispatch = row.groups()
        n = int(addr, 16)
        if not (addr == fn == dispatch) or n in entries:
            raise ValueError('duplicate or inconsistent generated registration')
        entries.add(n)
    return entries


def defined_text(symbols):
    entries = set()
    for line in symbols.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ('t', 'T'):
            m = re.fullmatch(r'_?f_([0-9a-f]+)', parts[0])
            if m:
                entries.add(int(m[1], 16))
    return entries


def compare(required, registered, defined=None):
    required = set(required)
    return dict(required=len(required), registered=len(required & registered),
                missing_registration=sorted(required - registered),
                missing_linked_text=None if defined is None else
                sorted((required & registered) - defined))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('registry', type=Path, help='generated recomp.c, not scan/all.txt')
    p.add_argument('--binary', type=Path, help='optional unstripped linked library')
    p.add_argument('--nm', default='nm')
    a = p.parse_args()
    try:
        required = audit(a.eboot.read_bytes())['required_roots']
        registered = registrations(a.registry.read_text())
        symbols = None if a.binary is None else defined_text(subprocess.check_output(
            [a.nm, '-P', str(a.binary.resolve())], text=True))
        result = compare(required, registered, symbols)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(2, f'{exc}\n')
    print(json.dumps(result))
    return int(bool(result['missing_registration'] or result['missing_linked_text']))


if __name__ == '__main__':
    raise SystemExit(main())
