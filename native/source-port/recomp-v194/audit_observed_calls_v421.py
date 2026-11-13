#!/usr/bin/env python3
"""Check a private replay's observed RcApi CALL edges against emitted C.
Input is the focused recomp.c, its instrumented shards and a private log.
Indirect calls establish a real emitted site and observed registered target,
not a statically proven set of targets. Only aggregate counts leave the tool.
Supports the pinned emitter's single-line call format; unknown shapes fail.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from audit_focused_registry_v417 import read

MAX_TOTAL = 512 << 20
MAX_FILES = 512
MAX_EDGES = 65536
HEX = r"[0-9a-f]{1,16}"
FUNC = re.compile(r'^(?:__attribute__\(\(visibility\("hidden"\)\)\) )?void f_(' + HEX + r')\(BbCpu \*c\) \{$')
CALL = re.compile(r"rc->call\(c, (t|B \+ 0x" + HEX + r"ull), B \+ 0x(" + HEX + r")ull\)")
CONST_T = re.compile(r"\bconst uint64_t t = B \+ 0x(" + HEX + r")ull;")
EVENT = re.compile(r"NATIVE_EDGE (" + HEX + r") (" + HEX + r")")


def sites(files, table):
    result, total = {}, 0
    if not files or len(files) > MAX_FILES:
        raise ValueError("invalid shard count")
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError("unsafe shard")
        caller = None
        with path.open("rb") as source:
            for raw in iter(lambda: source.readline(65537), b""):
                total += len(raw)
                if len(raw) > 65536 or total > MAX_TOTAL:
                    raise ValueError("shard budget exceeded")
                line = raw.decode("utf-8").rstrip()
                if (m := FUNC.fullmatch(line)):
                    caller = int(m[1], 16)
                if "rc->call(" not in line:
                    continue
                matches = CALL.findall(line)
                if len(matches) != 1 or line.count("rc->call(") != 1 or caller not in table:
                    raise ValueError("unknown emitted call shape")
                arg, next_hex = matches[0]
                next_ip = int(next_hex, 16)
                if not caller < next_ip <= caller + table[caller][0] or next_ip in result:
                    raise ValueError("ambiguous continuation")
                literal = CONST_T.search(line)
                result[next_ip] = (int(arg[6:-3], 16) if arg != "t" else
                                   int(literal[1], 16) if literal else None)
    return result


def observed(lines):
    edges = set()
    total = 0
    for line in lines:
        total += len(line)
        if total > 32 << 20:
            raise ValueError("trace budget exceeded")
        if not line.startswith("NATIVE_EDGE"):
            continue
        m = EVENT.fullmatch(line.rstrip("\r\n"))
        if not m:
            raise ValueError("malformed trace record")
        edges.add(tuple(int(x,16) for x in m.groups()))
        if len(edges) > MAX_EDGES:
            raise ValueError("too many observed edges")
    if not edges:
        raise ValueError("empty edge evidence")
    return edges


def verify(edges, site, table):
    direct = indirect = 0
    for target, next_ip in edges:
        if target not in table or next_ip not in site or target == next_ip:
            raise ValueError("unregistered target or unknown continuation")
        pinned = site[next_ip]
        if pinned is None:
            indirect += 1
        elif target == pinned:
            direct += 1
        else:
            raise ValueError("direct call target mismatch")
    return dict(direct_matches=direct, observed_indirect_matches=indirect,
                static_indirect_closure_proven=False)


def self_test():
    import tempfile
    table = {16:(16,1),32:(16,2),64:(8,3)}
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)/"recomp_00001.c"
        p.write_text('void f_10(BbCpu *c) {\n'
                     'rc->call(c, B + 0x20ull, B + 0x11ull);\n'
                     '{ const uint64_t t = B + 0x40ull; rc->call(c, t, B + 0x12ull); }\n'
                     '{ const uint64_t t = r[0]; rc->call(c, t, B + 0x13ull); }\n}\n')
        s = sites([p], table)
        report = verify(observed(["NATIVE_EDGE 20 11\n","NATIVE_EDGE 40 12\n","NATIVE_EDGE 20 13\n"]),s,table)
        assert report["direct_matches"]==2 and report["observed_indirect_matches"]==1
        for invalid in ({(64,17)},{(32,18)},{(99,19)},{(32,21)}):
            try:
                verify(invalid,s,table)
            except ValueError:
                continue
            raise AssertionError("invalid edge accepted")
        with p.open("a") as f:
            f.write("rc->call(c, t, B + 0x13ull);\n")
        try:
            sites([p],table)
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate continuation accepted")
    print("NATIVE_V421_OBSERVED_CALLS_PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--table",type=Path)
    p.add_argument("--shards",type=Path)
    p.add_argument("--trace",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test and not any((a.table,a.shards,a.trace)):
        self_test()
        return 0
    if a.self_test or not all((a.table,a.shards,a.trace)):
        p.error("choose self-test or supply all three private inputs")
    try:
        if a.shards.is_symlink() or a.trace.is_symlink() or not a.trace.is_file():
            raise ValueError("unsafe input")
        table=read(a.table)
        site=sites(sorted(a.shards.glob("recomp_*.c")),table)
        with a.trace.open(encoding="utf-8") as trace:
            result=verify(observed(iter(lambda:trace.readline(65537),"")),site,table)
        print(json.dumps(result,sort_keys=True))
        return 0
    except (ValueError,OSError):
        print("private CALL evidence refused",file=sys.stderr)
        return 2


if __name__=="__main__":
    sys.exit(main())
