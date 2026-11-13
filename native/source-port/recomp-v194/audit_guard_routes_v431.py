#!/usr/bin/env python3
"""Private-only evidence audit for exact startup guard routes.

Inputs are the pinned emitter's focused registration/shard files,
scanner import TSV, and the private C initializer list. A match checks
a direct emitted target and operation, not the provenance of a guard
address or execution of that route. Output contains counts only.
"""
import argparse
import json
from pathlib import Path
import re
import sys

from audit_focused_registry_v417 import read
from audit_observed_calls_v421 import sites
from audit_startup_prefix_v422 import lines

OPS = {b"__cxa_guard_acquire": b"ACQUIRE", b"__cxa_guard_release": b"RELEASE",
       b"__cxa_guard_abort": b"ABORT"}
HEX = rb"[0-9a-fA-F]{1,16}"
ROW = re.compile(rb"\{\s*0x("+HEX+rb")ull,\s*0x("+HEX+rb")ull,\s*0x("+HEX+
                 rb")ull,\s*SHYT_GUARD_(ACQUIRE|RELEASE|ABORT)\s*\},")
MAX = 65536


def imports(records):
    result = {}
    for record in records:
        fields = record.split(b"\t", 2)
        if len(fields) < 2 or not fields[0].startswith(b"0x"):
            continue
        if not re.fullmatch(HEX, fields[0][2:]):
            raise ValueError("malformed import target")
        addr = int(fields[0], 16)
        op = OPS.get(fields[1])
        if addr in result and result[addr] != op:
            raise ValueError("conflicting import identity")
        result[addr] = op
    return result


def audit(rows, service, emitted):
    if not 0 < len(rows) <= MAX:
        raise ValueError("invalid route count")
    previous = (-1, -1)
    continuations = set()
    for raw in rows:
        m = ROW.fullmatch(raw.strip())
        if not m:
            raise ValueError("malformed route")
        target, cont, guard = (int(v, 16) for v in m.groups()[:3])
        if (not target or not cont or target == cont or not guard or guard & 7
                or guard > (1 << 64) - 9 or (cont, guard) <= previous):
            raise ValueError("invalid or unsorted guard route")
        if service.get(target) != m[4] or emitted.get(cont) != target:
            raise ValueError("route does not match direct emitted import")
        previous = (cont, guard)
        continuations.add(cont)
    return dict(route_rows=len(rows), direct_continuations=len(continuations),
                guard_addresses_attested=False, runtime_attested=False)


def self_test():
    a = b"{0x10ull,0x20ull,0x4000ull,SHYT_GUARD_ACQUIRE},"
    b = a.replace(b"4000", b"4008")
    svc = imports([b"0x10\t__cxa_guard_acquire", b"0x30\t__cxa_guard_release"])
    assert audit([a,b], svc, {0x20:0x10})["direct_continuations"] == 1
    for rows, site in (([a,a],{0x20:0x10}), ([b,a],{0x20:0x10}),
                       ([a],{0x20:None}), ([a],{0x20:0x30}),
                       ([a.replace(b"ACQUIRE",b"RELEASE")],{0x20:0x10}),
                       ([a.replace(b"4000",b"4001")],{0x20:0x10})):
        try:
            audit(rows, svc, site)
        except ValueError:
            continue
        raise AssertionError("invalid guard evidence accepted")
    print("NATIVE_V431_GUARD_EVIDENCE_PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    for name in ("routes", "imports", "table", "shards"):
        p.add_argument("--"+name, type=Path)
    a = p.parse_args()
    paths = (a.routes, a.imports, a.table, a.shards)
    if a.self_test and not any(paths):
        self_test()
        return 0
    if a.self_test or not all(paths):
        p.error("choose --self-test or supply four private paths")
    try:
        if a.shards.is_symlink() or not a.shards.is_dir():
            raise ValueError("invalid shard directory")
        report = audit(lines(a.routes), imports(lines(a.imports)),
                       sites(sorted(a.shards.glob("recomp_*.c")), read(a.table)))
    except (ValueError, OSError):
        print("private guard evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
