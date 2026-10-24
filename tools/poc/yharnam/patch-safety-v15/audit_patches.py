#!/usr/bin/env python3
"""Read-only shadPS4 patch inventory and byte-accurate overlap check for Bloodborne 1.09.

Never applies patches or changes executable, save, process memory or online state.
"""
import argparse
from collections import defaultdict
from itertools import combinations
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

def data_for(line):
    typ, text = line.get('Type'), line.get('Value', '')
    if typ == 'bytes':
        raw = re.sub(r'\s+', '', text)
        if len(raw) % 2:
            raw = '0' + raw
        return bytes.fromhex(raw)
    if typ in {'bytes16', 'bytes32', 'bytes64'}:
        return int(text, 0).to_bytes(int(typ[5:]) // 8, 'little')
    if typ in {'float32', 'float64'}:
        return struct.pack('<f' if typ == 'float32' else '<d', float(text))
    if typ == 'utf16':
        return text.encode('utf-16-le')
    raise ValueError(f'Unsupported patch encoding: {typ!r}')

def audit(paths):
    enabled, disabled, writes, errors = [], [], defaultdict(list), []
    for filename in paths:
        path = Path(filename)
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            errors.append(f'{path.name}: {exc}')
            continue
        for m in root.findall('Metadata'):
            name = m.get('Name', 'Unnamed')
            on = m.get('isEnabled', 'false').lower() == 'true'
            item = {'source': path.name, 'name': name,
                    'version': m.get('AppVer'), 'app_elf': m.get('AppElf'),
                    'enabled': on, 'count': len(m.findall('./PatchList/Line'))}
            (enabled if on else disabled).append(item)
            if not on:
                continue
            if item['version'] != '01.09' or item['app_elf'] != 'eboot.bin':
                errors.append(f'{path.name}:{name}: not a 01.09 eboot patch; skipped')
                continue
            for idx, line in enumerate(m.findall('./PatchList/Line'), 1):
                try:
                    addr = int(line.attrib['Address'], 0)
                    blob = data_for(line)
                    for ofs, value in enumerate(blob):
                        writes[addr + ofs].append((path.name, name, idx, value))
                except (KeyError, ValueError, OverflowError) as exc:
                    errors.append(f'{path.name}:{name}: line {idx}: {exc}')
    overlaps = defaultdict(list)
    for addr, entries in writes.items():
        for a, b in combinations(entries, 2):
            if a[:2] == b[:2]:
                continue
            key = tuple(sorted((a[:2], b[:2])))
            overlaps[key].append((addr, a[3], b[3]))
    conflicts = []
    for key, points in overlaps.items():
        points.sort()
        different = [f'0x{addr:08X}' for addr, a, b in points if a != b]
        conflicts.append({
            'first': {'file': key[0][0], 'patch': key[0][1]},
            'second': {'file': key[1][0], 'patch': key[1][1]},
            'overlap_bytes': len(points),
            'different_bytes': len(different),
            'different_addresses': different,
            'first_overlap_address': f'0x{points[0][0]:08X}',
            'severity': 'conflict' if different else 'same-bytes',
        })
    conflicts.sort(key=lambda x: (-x['different_bytes'], -x['overlap_bytes']))
    return {'schema': 1,
            'scope': 'shadPS4 XML eboot 01.09 patch address space only',
            'enabled': enabled, 'disabled_count': len(disabled),
            'overlaps': conflicts, 'errors': errors,
            'fail_closed': bool(errors or any(x['different_bytes'] for x in conflicts))}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('xml', nargs='+', type=Path)
    p.add_argument('--json', type=Path, help='write machine-readable report')
    p.add_argument('--strict', action='store_true',
                   help='exit 2 on active conflicting patches or malformed metadata')
    opts = p.parse_args()
    data = audit(opts.xml)
    if opts.json:
        opts.json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
    print(f"XML game patches: {len(data['enabled'])} enabled, {data['disabled_count']} disabled")
    for item in data['overlaps']:
        print(f"[{item['severity'].upper()}] {item['first']['patch']} vs "
              f"{item['second']['patch']}: {item['overlap_bytes']} overlapping bytes, "
              f"{item['different_bytes']} differ")
    for err in data['errors']:
        print('ERROR:', err)
    return 2 if opts.strict and data['fail_closed'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
