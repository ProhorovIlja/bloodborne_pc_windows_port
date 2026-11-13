#!/usr/bin/env python3
"""Check private focused RcFunction identities against the whole-image table.
The table hash is the emitter's input-byte hash, not a hash of generated C,
and a matching row does not attest linked code or successful execution.
Only aggregate results are printed; don't publish either table.
"""
import argparse
import io
import json
from pathlib import Path
import re
import sys

HEADER = "static const RcFunction table[] = {"
ROW = re.compile(r"\{\s*0x([0-9a-fA-F]{1,16}),\s*([0-9]{1,10}),\s*0x([0-9a-fA-F]{1,16})ull,\s*f_([0-9a-fA-F]{1,16}),\s*&d_([0-9a-fA-F]{1,16})\s*\},")
MAX_BYTES = 64 << 20
MAX_ROWS = 1_000_000


def parse(lines):
    result = {}
    state = 0
    previous = -1
    for raw in lines:
        s = raw.strip()
        if s == HEADER:
            if state:
                raise ValueError("duplicate table")
            state = 1
        elif state == 1:
            if s == "};":
                state = 2
                continue
            row = ROW.fullmatch(s)
            if not row:
                raise ValueError("invalid registration row")
            address, size, digest, fn, slot = (
                int(x, 10 if i == 1 else 16) for i, x in enumerate(row.groups())
            )
            if address <= previous or address != fn or address != slot or not 0 < size <= 0xffffffff or len(result) == MAX_ROWS:
                raise ValueError("inconsistent registration row")
            result[address] = (size, digest)
            previous = address
    if state != 2 or not result:
        raise ValueError("missing or empty registration table")
    return result


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("unsafe table path")
    with path.open("rb") as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("table exceeds budget")
    return parse(io.StringIO(raw.decode("utf-8")))


def compare(focused, full):
    missing = sum(x not in full for x in focused)
    mismatched = sum(x in full and v != full[x] for x, v in focused.items())
    return dict(focused_rows=len(focused), whole_rows=len(full),
                matching_rows=len(focused)-missing-mismatched, missing_rows=missing,
                mismatched_rows=mismatched, linked_code_attested=False)


def self_test():
    def fixture(*rows):
        return parse([HEADER, *rows, "};"])
    a = "{0x10, 5, 0xabcull, f_10, &d_10},"
    b = "{0x20, 7, 0xdefull, f_20, &d_20},"
    full = fixture(a,b)
    if compare(fixture(b),full)["matching_rows"] != 1:
        raise AssertionError("subset not matched")
    for field in (" 5,", "abc"):
        altered = a.replace(field, " 6," if field == " 5," else "abd")
        if compare(fixture(altered),full)["mismatched_rows"] != 1:
            raise AssertionError("modified row accepted")
    missing = b.replace("20", "30")
    if compare(fixture(missing),full)["missing_rows"] != 1:
        raise AssertionError("unknown address accepted")
    for rows in ((a,a),(b,a),(a.replace("&d_10","&d_20"),),()):
        try:
            fixture(*rows)
        except ValueError:
            continue
        raise AssertionError("invalid table accepted")
    print("NATIVE_V417_FOCUSED_REGISTRY_PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--focused", type=Path)
    p.add_argument("--whole", type=Path)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test and not (a.focused or a.whole):
        self_test()
        return 0
    if a.self_test or not a.focused or not a.whole:
        p.error("choose --self-test or supply both tables")
    try:
        result = compare(read(a.focused), read(a.whole))
    except (ValueError,OSError):
        print("private table input refused",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return int(bool(result["missing_rows"] or result["mismatched_rows"]))


if __name__ == "__main__":
    sys.exit(main())
