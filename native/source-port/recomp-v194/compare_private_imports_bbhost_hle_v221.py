#!/usr/bin/env python3
"""V221: source-backed BBHost HLE registry vs PRIVATE Bloodborne import names.

Printed output contains AGGREGATES ONLY, never names/addresses/owners' bytes.
A registered HLE callback is not evidence of correct behavior or native ABI.
Public registry may include build-conditional hooks and unused registrations.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import tempfile

MAX_SOURCE = 3 * 1024 * 1024
MAX_FILES = 120
MAX_REGISTRATIONS = 3000
REGISTER = re.compile(r'\b(?:REG(?:_RAW)?|register_hle_fn(?:_raw)?)'
                      r'\s*\(\s*"([A-Za-z_][A-Za-z_0-9$@.?+-]{0,127})"\s*,')
ORIGINAL_ROW = re.compile(r'0x[0-9a-fA-F]{1,16}\t([^\t\r\n]{1,256})\Z')


def extract_public(root: Path) -> dict[str, str]:
    directory = root / 'src/hle'
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('missing public BBHost HLE source')
    files = sorted(directory.glob('*.cpp'))
    if not 5 <= len(files) <= MAX_FILES:
        raise ValueError('unexpected BBHost source count')
    registry: dict[str, str] = {}
    for source in files:
        if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_SOURCE:
            raise ValueError('unsafe BBHost source')
        text = source.read_text(encoding='utf-8')
        # Drop entire comment segments to avoid documenting disabled examples.
        text = re.sub(r'/\*.*?\*/|//[^\n]*', ' ', text, flags=re.S)
        for name in REGISTER.findall(text):
            if name in registry and registry[name] != source.stem:
                raise ValueError('ambiguous public registration module')
            registry[name] = source.stem
            if len(registry) > MAX_REGISTRATIONS:
                raise ValueError('too many public HLE registrations')
    if not registry:
        raise ValueError('no BBHost HLE registrations found')
    return registry


def read_public_names(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SOURCE:
        raise ValueError('unsafe public registry TSV')
    registry: dict[str, str] = {}
    for row in path.read_text(encoding='utf-8').splitlines():
        fields = row.split('\t')
        if len(fields) != 2 or not all(fields) or not re.fullmatch(
            r'[A-Za-z_][A-Za-z_0-9$@.?+-]{0,127}', fields[0]
        ) or not re.fullmatch(r'[a-z_0-9]{1,32}',fields[1]):
            raise ValueError('malformed public registry TSV')
        if fields[0] in registry and registry[fields[0]] != fields[1]:
            raise ValueError('ambiguous public registry name')
        registry[fields[0]] = fields[1]
        if len(registry) > MAX_REGISTRATIONS:
            raise ValueError('too many public registry rows')
    if not registry:
        raise ValueError('empty public registry')
    return registry


def read_private(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SOURCE:
        raise ValueError('private original import TSV unsafe')
    rows = path.read_text(encoding='utf-8').splitlines()
    if not rows or rows[0] != 'stub\tname' or not 0 < len(rows)-1 <= 2000:
        raise ValueError('not original scanner imports.tsv')
    names = []
    for row in rows[1:]:
        match = ORIGINAL_ROW.fullmatch(row)
        if not match:
            raise ValueError('malformed original scanner import row')
        names.append(match.group(1))
    return names


def compare(original: list[str], registry: dict[str, str]) -> dict:
    registered = [name for name in original if name in registry]
    by_module = Counter(registry[name] for name in registered)
    return {
        'format': 'SHYT_V221_PRIVATE_ORIGINAL_PUBLIC_BBHOST_HLE_AUDIT',
        'original_import_stub_rows': len(original),
        'original_names_with_public_registered_HLE': len(registered),
        'original_names_without_public_registered_HLE': len(original)-len(registered),
        'public_unique_registered_HLE_names': len(registry),
        'original_matching_modules': dict(sorted(by_module.items())),
        'registration_is_not_functional_implementation_proof': True,
        'conditional_compile_options_unresolved': True,
        'actual_Win64_native_abi_and_game_boot_proven': False,
        'private_game_import_names_exposed': False,
    }


def selftest() -> None:
    with tempfile.TemporaryDirectory() as dirname:
        root = Path(dirname)
        d = root / 'src/hle'
        d.mkdir(parents=True)
        for i in range(5):
            (d / f'm{i}.cpp').write_text(
                '#define REG(name,fn) register_hle_fn(name,fn)\n'
                + ('REG("sceTestOpen",fn);\nREG_RAW("sceTestRead",fn);\n'
                   if i == 0 else '/* REG("Fake",fn); */\n'))
        names = extract_public(root)
        assert names == {'sceTestOpen':'m0','sceTestRead':'m0'}, names
        tsv = root / 'private.tsv'
        tsv.write_text('stub\tname\n0x10\tsceTestOpen\n0x20\tmissing\n')
        report = compare(read_private(tsv), names)
        assert report['original_names_with_public_registered_HLE'] == 1
        assert report['original_names_without_public_registered_HLE'] == 1
        assert 'missing' not in json.dumps(report)
        pub = root/'public.tsv'
        pub.write_text('sceTestOpen\tm0\nsceTestRead\tm0\n')
        assert read_public_names(pub) == names
    print('SHYT_V221_PRIVATE_HLE_COVERAGE_SYNTHETIC_PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bbhost-source',type=Path)
    parser.add_argument('--public-registered',type=Path)
    parser.add_argument('--private-original-imports',type=Path)
    parser.add_argument('--emit-public-registered',type=Path)
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        selftest()
    else:
        if bool(args.bbhost_source) == bool(args.public_registered):
            parser.error('choose either BBHost public source or public registry TSV')
        try:
            mapping = (extract_public(args.bbhost_source) if args.bbhost_source else
                       read_public_names(args.public_registered))
            if args.emit_public_registered:
                if args.emit_public_registered.is_symlink():
                    raise ValueError('unsafe public registry output')
                args.emit_public_registered.write_text(
                    ''.join(f'{name}\t{module}\n' for name,module in
                            sorted(mapping.items())),encoding='utf-8')
            if args.private_original_imports:
                result=compare(read_private(args.private_original_imports),mapping)
                print(json.dumps(result,sort_keys=True,separators=(',',':')))
            else:
                print(json.dumps({
                    'format':'SHYT_V221_PUBLIC_BBHOST_HLE_REGISTRY',
                    'registered_HLE_names':len(mapping),
                    'registered_module_count':len(set(mapping.values())),
                    'no_original_game_input':True},separators=(',',':')))
        except (ValueError,OSError,UnicodeError) as exc:
            parser.error(str(exc))
