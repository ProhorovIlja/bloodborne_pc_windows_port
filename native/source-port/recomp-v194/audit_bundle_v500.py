# SPDX-License-Identifier: GPL-2.0-or-later
"""Find loose PS4 executables and uninspectable links in a prepared launch tree."""
import argparse
import json
import os
from pathlib import Path
import stat
import struct

from guest_payload_v517 import anchors, contains


def audit(root, signatures=()):
    root = Path(root)
    root_info = root.lstat()
    if not stat.S_ISDIR(root_info.st_mode) or getattr(root_info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('expected a real directory')
    hits = []
    files = 0
    def fail(error):
        raise error
    for base, dirs, names in os.walk(root, onerror=fail, followlinks=False):
        for name in dirs + names:
            p = Path(base) / name
            info = p.lstat()
            mode = info.st_mode
            lower = name.casefold()
            reason = None
            if stat.S_ISLNK(mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                if name in dirs:
                    dirs.remove(name)
                reason = 'link-or-reparse-point'
            elif lower in ('eboot.bin', 'eboot.bin-decrypted') or lower.endswith(('.prx', '.sprx')):
                reason = 'original-executable-name'
            elif stat.S_ISREG(mode):
                files += 1
                with p.open('rb') as stream:
                    h = stream.read(20)
                    embedded = contains(stream, signatures)
                if lower == 'guest_image.bin':
                    reason = 'known-guest-image-name'
                elif embedded:
                    reason = 'reference-guest-rx-window'
                elif h.startswith((b'BBPROBE2', b'BBPROBE3', b'BBPROBE4', b'BBPROBE5')):
                    reason = 'bbport-guest-image'
                elif h.startswith(b'\x4f\x15\x3d\x1d'):
                    reason = 'self-magic'
                elif (len(h) == 20 and h[:6] == b'\x7fELF\x02\x01'
                      and int.from_bytes(h[16:18], 'little') in (0xfe00, 0xfe01, 0xfe04, 0xfe10, 0xfe18)
                      and h[18:20] == b'\x3e\x00'):
                    reason = 'ps4-elf-header'
            elif not stat.S_ISDIR(mode):
                reason = 'non-regular-file'
            if reason:
                hits.append((p.relative_to(root).as_posix(), reason))
    if not files and not hits:
        raise ValueError('empty launch tree')
    return {'files_inspected': files, 'findings': sorted(hits), 'runtime_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--reference-elf', type=Path, help='private PS4 ELF for unmodified RX-window checks')
    args = parser.parse_args()
    try:
        report = audit(args.root, anchors(args.reference_elf) if args.reference_elf else ())
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(report, sort_keys=True))
    return 3 if report['findings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
