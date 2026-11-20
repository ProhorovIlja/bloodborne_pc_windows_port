#!/usr/bin/env python3
"""Offline, bounded direct-call analysis of the known Bloodborne 1.09 DT_INIT list.

Requires GNU objdump. Reports addresses only; this is a lower bound, not an
inventory of indirect/tail calls, callees, or dynamically reachable code.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
from pathlib import Path
import re
import struct
import subprocess
from tempfile import TemporaryDirectory


DIGEST = '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7'
FIRST, COUNT, REGISTRAR = 0x53e3bb8, 18444, 0x20b7b10
LINE = re.compile(r'^\s*([\da-f]+):\s+((?:[\da-f]{2} )+)\s*(\S+)(?:\s+(.*))?$')


def reachable_calls(start, ins):
    pending = [start]
    seen, calls = set(), set()
    while pending:
        pc = pending.pop()
        if pc in seen or pc not in ins:
            continue
        seen.add(pc)
        size, op, arg = ins[pc]
        match = re.match(r'0x([\da-f]+)\b', arg)
        target = int(match[1], 16) if match else None
        if op.startswith('ret') or op in ('ud2', 'int3', '(bad)', '.byte'):
            continue
        if op.startswith('j') and target is not None:
            pending.append(target)
        if op in ('jmp', 'jmpq'):
            continue
        if op in ('call', 'callq') and target == REGISTRAR:
            calls.add(pc)
        pending.append(pc + size)
    return tuple(sorted(calls))


def scan(data):
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError('expected the verified decrypted CUSA03173 1.09 ELF')
    reloc = {a: v for a, t, v in struct.iter_unpack(
        '<QQq', memoryview(data)[0x53f4d30:0x5951e78]) if t == 8}
    entries = [reloc[FIRST - 8*i] for i in range(COUNT)]
    text = data[0x4000:0x4000+0x2bbe4a8]
    starts = sorted(set(entries))
    candidates = {}
    for m in re.finditer(b'\xe8', text):
        pc = m.start()
        if pc+5 > len(text) or pc+5+struct.unpack_from('<i', text, pc+1)[0] != REGISTRAR:
            continue
        index = bisect_right(starts, pc)-1
        if index < 0 or pc-starts[index] >= 4096:
            continue
        candidates[starts[index]] = min(starts[index]+4096,
            starts[index+1] if index+1 < len(starts) else len(text))
    confirmed = {}
    with TemporaryDirectory(prefix='bb-init-') as tmp:
        path = Path(tmp)/'text'
        path.write_bytes(text)
        for start, end in sorted(candidates.items()):
            output = subprocess.check_output(['objdump', '-D', '-b', 'binary',
                '-mi386:x86-64', '-Mintel', '--insn-width=16', f'--start-address={start}',
                f'--stop-address={end}', str(path)], text=True)
            ins = {int(m[1],16): (len(bytes.fromhex(m[2])), m[3], m[4] or '')
                   for line in output.splitlines() if (m := LINE.match(line))}
            if calls := reachable_calls(start, ins):
                confirmed[start] = calls
    return len(starts), len(candidates), [(i, a, confirmed[a]) for i, a in enumerate(entries, 1)
        if a in confirmed]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decrypted_elf', type=Path)
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()
    try:
        unique, candidates, rows = scan(args.decrypted_elf.read_bytes())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'scan failed: {exc}\n')
    print(f'DT_INIT entries: {COUNT}; unique: {unique}; byte candidates: {candidates}; '
          f'entries with reachable direct registrar calls: {len(rows)}')
    print('per 1000 startup entries:', dict(sorted(Counter((n-1)//1000 for n, _, _ in rows).items())))
    if args.list:
        for n, start, calls in rows:
            print(n, hex(start), *(hex(pc) for pc in calls), sep='\t')


if __name__ == '__main__':
    main()
