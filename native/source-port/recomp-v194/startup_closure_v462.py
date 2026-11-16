#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline closure gate for a focused native startup build (Python 3.9+).

Input: normalized JSON, not an ELF or a donor's raw output. IDs are opaque.
constructors: the complete ordered list, including repeats (1-based).
functions: ID -> {calls: [...], indirect: [[candidate IDs], ...], imports: [...]}.
An empty indirect candidate list represents a site with no proven target set.
bindings: import -> native | unresolved | guest | interpreter | jit.
whole and focused: lists of function IDs in each generated inventory.
Only supply complete dependency rows and proven *complete* indirect target sets;
this checker does not prove either and never runs game code.
"""
import argparse
import collections
import json
import sys


def ids(values):
    if not isinstance(values, list) or any(type(x) is not str or not x for x in values):
        raise ValueError('expected a list of nonempty string IDs')
    return values


def unique(values):
    seq = ids(values)
    if len(seq) != len(set(seq)):
        raise ValueError('duplicate inventory ID')
    return set(seq)


def plan(data, start, end):
    order = ids(data['constructors'])
    if not 1 <= start <= end <= len(order):
        raise ValueError('invalid 1-based constructor range')
    whole, focused = unique(data['whole']), unique(data['focused'])
    if not focused <= whole:
        raise ValueError('focused inventory is not a subset of whole inventory')
    funcs, bindings = data['functions'], data['bindings']
    if not isinstance(funcs, dict) or not isinstance(bindings, dict):
        raise ValueError('expected function and binding maps')
    seen, add = set(), set()
    blockers = collections.Counter()
    first = None
    for index, root in enumerate(order[start - 1:end], start):
        todo = [root]
        while todo:
            f = todo.pop()
            if f in seen:
                continue
            seen.add(f)
            before = sum(blockers.values())
            if f not in whole:
                blockers['missing_whole'] += 1
            elif f not in focused:
                add.add(f)
            if f not in funcs:
                blockers['missing_dependency_row'] += 1
            else:
                row = funcs[f]
                if not isinstance(row, dict) or set(row) != {'calls', 'indirect', 'imports'}:
                    raise ValueError('incomplete or invalid dependency row')
                todo.extend(ids(row['calls']))
                if not isinstance(row['indirect'], list):
                    raise ValueError('invalid indirect sites')
                for targets in row['indirect']:
                    if not ids(targets):
                        blockers['unresolved_indirect_site'] += 1
                    todo.extend(targets)
                for name in ids(row['imports']):
                    if bindings.get(name) != 'native':
                        blockers['import_without_native_binding'] += 1
            if first is None and sum(blockers.values()) != before:
                first = index
    return dict(constructor_count=end-start+1, reachable_count=len(seen),
                first_blocked_constructor=first, blockers=dict(sorted(blockers.items())),
                add_count=len(add)), sorted(add)


def load(stream):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    return json.load(stream, object_pairs_hook=pairs)


def self_test():
    def row(calls=(), indirect=(), imports=()):
        return dict(calls=list(calls), indirect=list(indirect), imports=list(imports))
    d = dict(constructors=['a','a','b','c'], whole=['a','b','c','helper'],
             focused=['a','b','c'], bindings={'lock':'native'},
             functions={'a':row(indirect=[['helper']]), 'helper':row(['a'], imports=['lock']),
                        'b':row(indirect=[[]]), 'c':row(['outside'])})
    report, additions = plan(d, 1, 4)
    assert report == dict(constructor_count=4, reachable_count=5,
                          first_blocked_constructor=3, add_count=1,
                          blockers={'unresolved_indirect_site':1,'missing_whole':1,
                                    'missing_dependency_row':1})
    assert additions == ['helper']
    report, _ = plan(d, 1, 2)
    assert not report['blockers'] and report['add_count'] == 1
    d['focused'].append('helper')
    assert plan(d, 1, 2)[0]['add_count'] == 0
    for mode in ['guest','unresolved','interpreter','jit',None]:
        d['bindings']['lock'] = mode
        assert plan(d, 1, 2)[0]['first_blocked_constructor'] == 1
    for bounds in [(0,1),(3,2),(1,5)]:
        try:
            plan(d, *bounds)
        except ValueError:
            continue
        raise AssertionError('invalid bounds accepted')
    print('startup closure fixture tests passed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', nargs='?')
    p.add_argument('--start', type=int)
    p.add_argument('--end', type=int)
    p.add_argument('--private-add-list', help='new local JSON file; never publish it')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        self_test()
        return 0
    if a.input is None or a.start is None or a.end is None:
        p.error('input, --start and --end required')
    try:
        with open(a.input, encoding='utf-8') as f:
            report, add = plan(load(f), a.start, a.end)
        if a.private_add_list and not report['blockers']:
            with open(a.private_add_list, 'x', encoding='utf-8') as f:
                json.dump(add, f)
        print(json.dumps(report, sort_keys=True))
        return 2 if report['blockers'] else 1 if add else 0
    except (KeyError, TypeError, ValueError, OSError):
        print('invalid input or unavailable file', file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
