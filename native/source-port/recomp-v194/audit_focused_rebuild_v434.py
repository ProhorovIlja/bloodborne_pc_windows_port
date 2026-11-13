#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Check a private focused AOT rebuild against its baseline and CALL trace.

The old emitted shards establish observed CALL sites. The new shards must
independently confirm those continuations and their direct/indirect shape.
Registry parity is emitter-input identity only, not linked-code attestation.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile

from audit_focused_registry_v417 import read, compare
from audit_indirect_gap_v433 import classify
from audit_observed_calls_v421 import observed, sites, verify


def check(old, new, whole, before, after, edges, max_extra):
    report, wanted = classify(old, whole, before, edges)
    if not wanted:
        raise ValueError("no observed indirect gap to verify")
    parity = compare(new, whole)
    if parity["missing_rows"] or parity["mismatched_rows"] or old.keys() - new.keys():
        raise ValueError("rebuilt registry changed or lost input identities")
    added = new.keys() - old.keys()
    required = set(wanted)
    if not required <= added or len(added - required) > max_extra:
        raise ValueError("missing target or unapproved expansion")
    for _, continuation in edges:
        if continuation not in after or before[continuation] != after[continuation]:
            raise ValueError("rebuilt CALL shape changed")
    verify(edges, after, new)
    return {
        "baseline_rows": len(old),
        "rebuilt_rows": len(new),
        "required_targets_added": len(required),
        "additional_rows": len(added - required),
        "observed_edges_rechecked": len(edges),
        "linked_code_attested": False,
        "retail_replay_verified": False,
        "static_indirect_closure_proven": False,
    }


def shard_sites(root, table):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("invalid shard directory")
    paths = []
    for path in root.glob("recomp_*.c"):
        if len(paths) == 512:
            raise ValueError("too many shards")
        paths.append(path)
    return sites(sorted(paths), table)


def self_test():
    old = {16: (16, 1), 32: (16, 2)}
    whole = {**old, 64: (8, 3), 80: (8, 4)}
    new = {**old, 64: whole[64]}
    edges = observed(["NATIVE_EDGE 20 11\n", "NATIVE_EDGE 40 12\n"])
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shard = root / "recomp_00001.c"
        code = ('void f_10(BbCpu *c) {\n'
                'rc->call(c, B + 0x20ull, B + 0x11ull);\n'
                'rc->call(c, t, B + 0x12ull);\n}\n')
        shard.write_text(code, encoding="utf-8")
        before = shard_sites(root, old)
        shard.write_text(code + 'void f_40(BbCpu *c) {\n}\n', encoding="utf-8")
        after = shard_sites(root, new)
        result = check(old, new, whole, before, after, edges, 0)
        assert result["required_targets_added"] == 1 and result["observed_edges_rechecked"] == 2
        assert not result["retail_replay_verified"]
        assert check(old, whole, whole, before, after, edges, 1)["additional_rows"] == 1
        for registry, changed, evidence in (
            (old, after, edges),
            (whole, after, edges),
            ({16: old[16], 64: new[64]}, after, edges),
            ({**new, 64: (8, 9)}, after, edges),
            ({**new, 32: (17, 2)}, after, edges),
            (new, {**after, 18: 64}, edges),
            (new, {17: 32}, edges),
            (new, after, {(32, 17)}),
        ):
            try:
                check(old, registry, whole, before, changed, evidence, 0)
            except ValueError:
                continue
            raise AssertionError("invalid rebuild accepted")
    print("NATIVE_V434_FOCUSED_REBUILD_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    for name in ("baseline", "rebuilt", "whole", "baseline-shards", "rebuilt-shards", "trace"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--max-extra", type=int, default=0)
    args = parser.parse_args()
    paths = (args.baseline, args.rebuilt, args.whole, args.baseline_shards,
             args.rebuilt_shards, args.trace)
    if args.self_test and not any(paths) and not args.max_extra:
        self_test()
        return 0
    if args.self_test or not all(paths) or not 0 <= args.max_extra <= 65536:
        parser.error("use --self-test or provide all six private paths and a bounded expansion budget")
    try:
        if any(path.is_symlink() for path in paths):
            raise ValueError("unsafe private input")
        if len({(p.stat().st_dev, p.stat().st_ino) for p in paths}) != len(paths):
            raise ValueError("duplicate private input")
        if not args.trace.is_file():
            raise ValueError("invalid trace")
        old, new, whole = map(read, paths[:3])
        with args.trace.open(encoding="utf-8") as stream:
            edges = observed(iter(lambda: stream.readline(65537), ""))
        result = check(old, new, whole, shard_sites(args.baseline_shards, old),
                       shard_sites(args.rebuilt_shards, new), edges, args.max_extra)
    except (ValueError, OSError):
        print("private focused rebuild evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
