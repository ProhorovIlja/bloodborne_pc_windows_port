# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the local continuation chain with attested direct setjmp resumes."""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_resume_branch_v674 import decode
from audit_resume_return_v676 import scan
from audit_setjmp_v673 import audit


def classify(blob, sites, blocks, returns):
    for pc, offset in sorted(set(sites)):
        branch = decode(blob, offset, pc)
        if branch is None:
            yield pc, 'branch'
            continue
        block = blocks.get(branch[1])
        if block is None:
            yield pc, 'block'
            continue
        zeroed, target, _ = block
        tail = returns.get(target)
        if tail is None:
            yield pc, 'epilogue'
            continue
        if tail[0] != (0, 4, 5, -1)[zeroed]:
            yield pc, 'register_contract'
            continue
        yield pc, 'through_ret'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--extra-entries', type=Path,
                   help='write new private hex-RVA list for external AOT tools')
    args = p.parse_args()
    sites = []
    audit(args.eboot, resumes=sites)
    blocks, _, returns, _ = scan(args.eboot, resumes=sites)
    rows = list(classify(args.eboot.read_bytes(), sites, blocks, returns))
    missing = {pc for pc, status in rows if status != 'through_ret'}
    if args.extra_entries:
        with args.extra_entries.open('x') as out:
            out.writelines(f'{pc:#x}\n' for pc in sorted(missing))
    print(json.dumps(dict(direct_resumes=len(rows), missing_entries=len(missing),
                          stages=dict(Counter(status for _, status in rows))), sort_keys=True))


if __name__ == '__main__':
    main()
