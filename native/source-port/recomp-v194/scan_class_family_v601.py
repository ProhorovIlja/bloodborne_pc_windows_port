#!/usr/bin/env python3
"""Classify the #90 family offline; structural match, not a proof of equivalence."""
import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from scan_init_classes_v600 import LINE, scan


def signature(text, start, size, base_slot=-1):
    out = subprocess.check_output(['objdump', '-D', '-b', 'binary',
        '-mi386:x86-64', '-Mintel', '--insn-width=16', f'--start-address={start}',
        f'--stop-address={start+size}', str(text)], text=True)
    ops, aliases, base = [], {}, None
    for line in out.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        off, op = int(m[1], 16)-start, m[3]
        arg, _, comment = (m[4] or '').partition('#')
        arg = arg.strip()
        if op.startswith('j') and arg.startswith('0x'):
            arg = hex(int(arg, 16)-start)
        elif op == 'call' and off == base_slot:
            base = int(arg, 16)
            arg = 'base-getter'
        elif 'rip' in arg:
            target = int(comment.strip(), 16)
            index = aliases.setdefault(target, len(aliases))
            arg = re.sub(r'rip[+-]0x[0-9a-f]+', f'rip+ref{index}', arg)
        ops.append((off, len(bytes.fromhex(m[2])), op, arg))
    return tuple(ops), base


def classify(data):
    _, _, rows = scan(data)
    _, ref, ref_calls = next(row for row in rows if row[0] == 90)
    with TemporaryDirectory(prefix='bb-family-') as tmp:
        text = Path(tmp)/'text'
        text.write_bytes(data[0x4000:0x4000+0x2bbe4a8])
        plen, clen, slot, glen = ref_calls[0]-ref+5, 0x3d9, 0x379, 0x1d8
        prefix, _ = signature(text, ref, plen)
        full, getter = signature(text, ref, clen, slot)
        gref, _ = signature(text, getter, glen)
        counts, results = Counter(), []
        for n, a, calls in rows:
            if calls[0]-a+5 != plen or signature(text, a, plen)[0] != prefix:
                continue
            counts['prefix'] += 1
            if len(calls) != 1:
                continue
            sig, g = signature(text, a, clen, slot)
            if sig != full:
                continue
            results.append((n, a, g))
        targets = {g for _, _, g in results}
        match = {g for g in targets if signature(text, g, glen)[0] == gref}
    return counts['prefix'], results, targets, match


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('decrypted_elf', type=Path)
    p.add_argument('--list', action='store_true')
    args = p.parse_args()
    try:
        prefixes, rows, targets, match = classify(args.decrypted_elf.read_bytes())
    except (OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as exc:
        p.exit(2, f'classification failed: {exc}\n')
    print(f'prefixes={prefixes} full_shapes={len(rows)} before_264={sum(n<264 for n, _, _ in rows)}')
    print(f'base_targets={len(targets)} getter_shapes={len(match)} covered_rows={sum(g in match for _, _, g in rows)}')
    if args.list:
        for n, a, g in rows:
            print(n, hex(a), hex(g), 'getter-shape' if g in match else 'manual', sep='\t')


if __name__ == '__main__':
    main()
