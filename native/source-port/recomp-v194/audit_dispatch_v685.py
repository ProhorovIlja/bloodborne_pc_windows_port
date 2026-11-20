# SPDX-License-Identifier: GPL-2.0-or-later
"""Union of guarded and simple native continuations; no guest fallback."""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_guarded_resume_v683 import census
from audit_resume_gaps_v681 import classify
from audit_resume_return_v676 import scan
from audit_setjmp_v673 import audit


def plan(path):
    sites = []
    audit(path, resumes=sites)
    blocks, _, returns, _ = scan(path, resumes=sites)
    rows = dict(classify(path.read_bytes(), sites, blocks, returns))
    guards = census(path)
    covered = set()
    for pc, _, _, _ in guards:
        if pc not in rows or rows[pc] == 'through_ret' or pc in covered:
            raise ValueError('ambiguous guarded continuation')
        covered.add(pc)
        rows[pc] = 'guarded_ret_or_fatal'
    return rows, guards


def emit(guards):
    lines = ['#include <stdint.h>', '#include <stddef.h>',
             'size_t bb_guarded_words(uint64_t pc) {', '    switch (pc) {']
    for pc, _, _, (_, _, _, _, skip, pops, _) in sorted(guards):
        lines.append(f'    case 0x{pc:x}: return {skip+len(pops)+1};')
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--emit-c', type=Path, help='new private dispatcher metadata')
    p.add_argument('--extra-entries', type=Path, help='new private uncovered RVA list')
    a = p.parse_args()
    rows, guards = plan(a.eboot)
    missing = sorted(pc for pc, s in rows.items() if s not in ('through_ret', 'guarded_ret_or_fatal'))
    if a.emit_c:
        with a.emit_c.open('x') as f:
            f.write(emit(guards))
    if a.extra_entries:
        with a.extra_entries.open('x') as f:
            f.writelines(f'{pc:#x}\n' for pc in missing)
    print(json.dumps(dict(sites=len(rows), missing=len(missing), stages=Counter(rows.values())), sort_keys=True))


if __name__ == '__main__':
    main()
