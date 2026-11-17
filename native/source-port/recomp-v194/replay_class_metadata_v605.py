#!/usr/bin/env python3
"""Send normalized class metadata to a previously built V605 fixture.

The dump is opened here, not by the native fixture. No executable bytes,
names, or raw game addresses are passed to the subprocess.
"""
import argparse
from pathlib import Path
import subprocess
from scan_class_metadata_v604 import inventory


def encode(rows):
    ids = {address: i for i, address in enumerate(sorted({a for r in rows for a in r[1:3]}))}
    keys = {address: i for i, address in enumerate(sorted({a for r in rows for a in r[4:]}))}
    return ''.join(' '.join(map(str, (n, ids[child], ids[parent], length, *(keys[k] for k in slots)))) + '\n'
                   for n, child, parent, length, *slots in rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('decrypted_elf', type=Path)
    p.add_argument('native_fixture', type=Path)
    args = p.parse_args()
    try:
        rows = inventory(args.decrypted_elf.read_bytes())
        result = subprocess.run([str(args.native_fixture.resolve(strict=True))],
                                input=encode(rows), text=True, timeout=30, check=False)
    except (ValueError, KeyError, OSError, StopIteration, subprocess.SubprocessError) as exc:
        p.exit(2, f'replay setup failed: {exc}\n')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
