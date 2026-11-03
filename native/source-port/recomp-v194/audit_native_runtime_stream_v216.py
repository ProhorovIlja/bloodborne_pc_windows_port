#!/usr/bin/env python3
"""V216: constant-memory lexical audit of generated original-game AOT C.

Counts guest runtime callbacks without exposing source, identifiers, game
offsets or binary data. Checks comments, strings and character literals.
Use on the owner's PRIVATE generated sources, not public CI.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

TOKENS = re.compile(r'/\*|//|"|\'')
CALLBACK = re.compile(r'\brc\s*->\s*(step|call|tail|bail|trace)\s*\(')
NAMES = ('step', 'call', 'tail', 'bail', 'trace')
MAX_LINE = 2 * 1024 * 1024
MAX_SOURCE = 64 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024 * 1024
MAX_FILES = 3000

def clean_line(line: str, state: str) -> tuple[str, str]:
    out: list[str] = []
    pos = 0
    size = len(line)
    while pos < size:
        if state == 'block':
            end = line.find('*/', pos)
            if end < 0:
                return ''.join(out) + '\n', 'block'
            pos = end + 2
            out.append(' ')
            state = 'code'
            continue
        if state in ('string', 'char'):
            delimiter = '"' if state == 'string' else "'"
            while pos < size:
                c = line[pos]
                pos += 1
                if c == '\\' and pos < size:
                    pos += 1
                elif c == delimiter:
                    state = 'code'
                    out.append(' ')
                    break
            if state != 'code':
                return ''.join(out) + '\n', state
            continue
        hit = TOKENS.search(line, pos)
        if not hit:
            out.append(line[pos:])
            break
        out.append(line[pos:hit.start()])
        token = hit.group()
        pos = hit.end()
        out.append(' ')
        if token == '//':
            out.append('\n')
            break
        if token == '/*':
            state = 'block'
        elif token == '"':
            state = 'string'
        else:
            state = 'char'
    return ''.join(out), state

def count_file(path: Path) -> Counter[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SOURCE:
        raise ValueError('generated C path/size is unsafe')
    state = 'code'
    previous = ''
    counts: Counter[str] = Counter()
    with path.open(encoding='utf-8') as source:
        for line in source:
            if len(line) > MAX_LINE:
                raise ValueError('unbounded generated C source line')
            code, state = clean_line(line, state)
            combined = previous + code
            for hit in CALLBACK.finditer(combined):
                if hit.end() > len(previous):
                    counts[hit.group(1)] += 1
            previous = combined[-128:]
            if not previous.endswith((' ', '\n')):
                previous += '\n'
    if state in ('block', 'string', 'char'):
        raise ValueError('unterminated generated C comment/string')
    return counts

def audit(folder: Path) -> dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('generated directory unsafe')
    files = sorted(folder.glob('recomp*.c'))
    if not 2 <= len(files) <= MAX_FILES or not (folder / 'recomp.c').is_file():
        raise ValueError('original AOT C source set missing')
    if any(not re.fullmatch(r'recomp(?:_[0-9a-fA-F]{5})?\.c', p.name) for p in files):
        raise ValueError('unexpected source filename')
    if sum(p.stat().st_size for p in files) > MAX_TOTAL:
        raise ValueError('generated source set too large')
    totals: Counter[str] = Counter()
    with_callbacks = 0
    for path in files:
        one = count_file(path)
        totals.update(one)
        if sum(one.values()):
            with_callbacks += 1
    return {
        'generated_c_files': len(files),
        'files_with_callbacks': with_callbacks,
        'callback_invocations': {name: totals[name] for name in NAMES},
        'callback_total': sum(totals.values()),
        'strict_native_runtime_ready': not any(totals.values()),
        'native_game_boot_proven': False,
        'original_game_bytes_emitted': False,
    }

def selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'recomp.c'
        path.write_text('/* rc->step(1) */\nchar *s="rc->call(2)";\n'
                        'rc -> bail(a); rc->step(a); // rc->trace(a)\n'
                        'rc/*cross*/->tail(a);\nrc ->\n call (b);\n'
                        '/* rc->bail(c)\n rc->tail(d) */\n')
        found = count_file(path)
        assert dict(found) == {'bail': 1, 'step': 1, 'tail': 1, 'call': 1}, found
        path.write_text('/* open comment\n')
        try:
            count_file(path)
        except ValueError:
            pass
        else:
            raise AssertionError('unterminated comment accepted')
    print('SHYT_V216_BOUNDED_SOURCE_LEXER_SELFTEST_PASS')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--generated-dir', type=Path)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        selftest()
    elif args.generated_dir:
        print(json.dumps(audit(args.generated_dir), separators=(',', ':')))
    else:
        ap.error('requires --generated-dir or --self-test')
