# SPDX-License-Identifier: GPL-2.0-or-later
"""Bind the audited error-publication family to native V573 category IDs."""
import argparse
from pathlib import Path
from audit_startup_tables_v644 import audit
from replay_guarded_v643 import normalize


def generate(blob):
    rows, tables = audit(blob)
    plan, slots, targets = normalize(rows)
    points = dict.fromkeys(r[3] for r in rows)
    categories = [tables[point][0] for point in points]
    if slots != 3 or targets != 3 or sorted(categories) != [0, 1, 2]:
        raise ValueError('unexpected publication inventory')
    bindings = {}
    yield '/* Private build input. Do not distribute. */'
    for ordinal, slot, target in plan:
        category = categories[target]
        if bindings.setdefault(slot, category) != category:
            raise ValueError('one object has conflicting native bindings')
        yield f'    {{{ordinal}, {slot}, {category}}},'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    a = p.parse_args()
    print('\n'.join(generate(a.eboot.read_bytes())))


if __name__ == '__main__':
    main()
