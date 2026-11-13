#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Classify an observed startup CALL missing from the focused AOT registry.

Supply a private NATIVE_EDGE trace and instrumented focused C shards in the
V421 format. A missing edge must actually be an indirect emitted CALL and its
target must be registered in the matching whole-image table. The report emits
only counts; this does not bind targets, prove closure, or attest execution.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from audit_focused_registry_v417 import compare, read
from audit_observed_calls_v421 import observed, sites, verify


def classify(focused, whole, call_sites, edges):
    parity = compare(focused, whole)
    if parity["missing_rows"] or parity["mismatched_rows"]:
        raise ValueError("registry disagreement")
    known = set()
    missing = set()
    for target, continuation in edges:
        if continuation not in call_sites or not target or target == continuation:
            raise ValueError("invalid observed edge")
        if target in focused:
            known.add((target, continuation))
        elif call_sites[continuation] is None and target in whole:
            missing.add((target, continuation))
        else:
            raise ValueError("missing target not an evidenced indirect gap")
    if known:
        verify(known, call_sites, focused)
    targets = sorted({target for target, _ in missing})
    return {
        "verified_focused_edges": len(known),
        "whole_only_indirect_edges": len(missing),
        "whole_only_targets": len(targets),
        "static_indirect_closure_proven": False,
        "linked_code_attested": False,
    }, targets


def write_private(path, targets):
    # Explicit opt-in, never overwrite, never use stdout for addresses.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii", newline="\n") as out:
        out.writelines(f"{target:x}\n" for target in targets)


def self_test():
    import tempfile

    focused = {0x10: (16, 1), 0x40: (8, 2)}
    whole = {**focused, 0x60: (8, 3), 0x80: (8, 4)}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shard = root / "recomp_00001.c"
        shard.write_text(
            'void f_10(BbCpu *c) {\n'
            'rc->call(c, B + 0x40ull, B + 0x11ull);\n'
            '{ const uint64_t t = r[0]; rc->call(c, t, B + 0x12ull); }\n'
            '{ const uint64_t t = r[1]; rc->call(c, t, B + 0x13ull); }\n}\n',
            encoding="utf-8",
        )
        call_sites = sites([shard], focused)
        evidence = observed([
            "NATIVE_EDGE 40 11\n", "NATIVE_EDGE 80 12\n",
            "NATIVE_EDGE 60 12\n", "NATIVE_EDGE 60 13\n",
            "NATIVE_EDGE 60 13\n",
        ])
        report, targets = classify(focused, whole, call_sites, evidence)
        assert report["verified_focused_edges"] == 1
        assert report["whole_only_indirect_edges"] == 3
        assert report["whole_only_targets"] == 2 and targets == [0x60, 0x80]
        assert not report["static_indirect_closure_proven"]
        assert classify(focused, whole, call_sites, {(0x40, 0x11)})[1] == []
        for registry, edges in [
            ({**whole, 0x10: (16, 9)}, evidence),
            (whole, {(0x60, 0x11)}),  # would change a direct call
            (whole, {(0x80, 0x14)}),  # unknown continuation
            (whole, {(0x99, 0x12)}),  # unknown target
            (whole, {(0x40, 0x10)}),
        ]:
            try:
                classify(focused, registry, call_sites, edges)
            except ValueError:
                continue
            raise AssertionError("accepted invalid evidence")
        plan = root / "private.txt"
        write_private(plan, targets)
        assert plan.read_bytes() == b"60\n80\n"
        if os.name == "posix":
            assert plan.stat().st_mode & 0o077 == 0
        try:
            write_private(plan, [])
        except FileExistsError:
            pass
        else:
            raise AssertionError("overwrote a private file")
    print("NATIVE_V433_INDIRECT_GAP_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    for name in ("focused", "whole", "shards", "trace", "private-targets"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    inputs = (args.focused, args.whole, args.shards, args.trace)
    if args.self_test and not any((*inputs, args.private_targets)):
        self_test()
        return 0
    if args.self_test or not all(inputs):
        parser.error("use --self-test or supply --focused --whole --shards --trace")
    try:
        if (args.shards.is_symlink() or not args.shards.is_dir()
                or args.trace.is_symlink() or not args.trace.is_file()
                or args.focused.resolve() == args.whole.resolve()):
            raise ValueError("unsafe or duplicate input")
        focused, whole = read(args.focused), read(args.whole)
        paths = []
        for path in args.shards.glob("recomp_*.c"):
            if len(paths) == 512:
                raise ValueError("too many shards")
            paths.append(path)
        call_sites = sites(sorted(paths), focused)
        with args.trace.open(encoding="utf-8") as trace:
            edges = observed(iter(lambda: trace.readline(65537), ""))
        report, targets = classify(focused, whole, call_sites, edges)
        if args.private_targets is not None:
            write_private(args.private_targets, targets)
    except (ValueError, OSError):
        print("private indirect CALL evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return int(bool(targets))


if __name__ == "__main__":
    raise SystemExit(main())
