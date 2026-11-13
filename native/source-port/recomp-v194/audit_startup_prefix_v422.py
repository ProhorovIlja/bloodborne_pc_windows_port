#!/usr/bin/env python3
"""Original-free check for private startup replay transcripts (not runtime attestation)."""
import argparse
import json
from pathlib import Path
import re

LIMIT = 32 << 20
RETURN = re.compile(rb"RETURN ([1-9][0-9]{0,5})")
FAIL = (b"PRIVATE_FAIL", b"AddressSanitizer", b"UndefinedBehaviorSanitizer",
        b"runtime error:", b"NATIVE_EDGE ", b"BIND422 ")
SUCCESS = b"PRIVATE_V413_REAL_FIRST_RETAIL_CTOR_RETURNED_PASS"


def lines(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("invalid input path")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT or not data.endswith(b"\n") or b"\0" in data:
        raise ValueError("truncated or oversized transcript")
    return data.splitlines()


def verify(out, err, first, last):
    if not 1 <= first <= last <= 65536:
        raise ValueError("invalid ordinal bounds")
    if not out or out[-1] != SUCCESS or out.count(SUCCESS) != 1:
        raise ValueError("missing unique terminal marker")
    ordinal = first
    for line in err:
        if any(token in line for token in FAIL):
            raise ValueError("failure or discovery marker")
        if line.startswith(b"RETURN"):
            m = RETURN.fullmatch(line)
            if not m or ordinal > last or int(m[1]) != ordinal:
                raise ValueError("unexpected return record")
            ordinal += 1
    if ordinal != last + 1:
        raise ValueError("incomplete return sequence")
    return ordinal - first


def self_test():
    good = [b"RETURN 93", b"RETURN 94"]
    assert verify([SUCCESS], good, 93, 94) == 2
    for out, err in (([], good), ([SUCCESS], good[:1]),
                     ([SUCCESS], good[::-1]), ([SUCCESS], good + good),
                     ([SUCCESS], good + [b"runtime error: bad"]),
                     ([SUCCESS], good + [b"NATIVE_EDGE 5 6"]),
                     ([SUCCESS, b"later"], good)):
        try:
            verify(out, err, 93, 94)
        except ValueError:
            continue
        raise AssertionError("invalid transcript accepted")
    print("NATIVE_V422_PREFIX_AUDIT_PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--first", type=int, default=93)
    p.add_argument("--last", type=int)
    p.add_argument("--run", type=Path, nargs=2, action="append",
                   metavar=("STDOUT", "STDERR"))
    a = p.parse_args()
    if a.self_test and not a.run and a.last is None:
        self_test()
        return 0
    if a.self_test or not a.run or a.last is None or len(a.run) > 8:
        p.error("choose self-test or 1–8 transcript pairs and a final ordinal")
    try:
        paths = [p.resolve() for pair in a.run for p in pair]
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate input path")
        counts = [verify(lines(out), lines(err), a.first, a.last)
                  for out, err in a.run]
    except (ValueError, OSError):
        print("private startup transcript refused")
        return 2
    print(json.dumps(dict(runs=len(counts), first=a.first, last=a.last,
                          records_per_run=counts[0], runtime_attested=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
