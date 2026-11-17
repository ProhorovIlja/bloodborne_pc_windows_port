# SPDX-License-Identifier: GPL-2.0-or-later
"""Build and run the complete resume fixture from a private 1.09 dump."""
import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from audit_resume_block_v675 import emit as emit_blocks
from audit_resume_branch_v674 import audit, decode, emit as emit_branches
from audit_resume_return_v676 import scan, emit as emit_returns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    previous, _, returns, _ = scan(args.eboot)
    sites = []
    audit(args.eboot, resumes=sites)
    blob = args.eboot.read_bytes()
    branches = [(pc, *b) for pc, off in sites if (b := decode(blob, off, pc)) is not None]
    rows = []
    for pc, _, nonzero in branches:
        if nonzero not in previous:
            continue
        z, target, _ = previous[nonzero]
        if target not in returns:
            continue
        src, skip, pops, _ = returns[target]
        if src != (0, 4, 5)[z]:
            raise ValueError('unexpected zeroed register')
        slots = ', '.join(str(pops.index(i)+skip if i in pops else -1) for i in range(6))
        rows.append(f'{{{pc}, {skip+len(pops)+1}, {src}, {{{slots}}}}},')
    if not rows:
        raise ValueError('no supported paths')
    with TemporaryDirectory(prefix='bb677-') as temp:
        tmp = Path(temp)
        (tmp / 'cases677.inc').write_text('\n'.join(rows)+'\n')
        inputs = []
        for name, body in (('branches', emit_branches(branches)),
                           ('blocks', emit_blocks(previous)), ('returns', emit_returns(returns))):
            path = tmp / (name+'.c')
            path.write_text(body)
            inputs.append(str(path))
        exe = tmp / 'test'
        source = Path(__file__).resolve().with_name('test_resume_chain_v677.c')
        subprocess.run([args.cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-no-pie', '-I', temp,
                        str(source), *inputs, '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=30)


if __name__ == '__main__':
    main()
