#!/usr/bin/env python3
"""Native V400: fail-closed original-free function hash/size/bytes tests.

The *real pinned upstream* generated table is checked separately in CI.
This file deliberately corrupts independent fixture/code/table values,
and verifies that none can become a published native function identity.
"""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "v400_identity",P/"verify_native_function_identity_v400.py")
assert spec and spec.loader
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
fn=importlib.util.spec_from_file_location(
    "v395_invented",P/"generate_verified_imports_v395.py")
assert fn and fn.loader
generated=importlib.util.module_from_spec(fn)
fn.loader.exec_module(generated)
fixture=v.load_fixture(P/"native_function_identity_fixture_v400.json")
image=generated.build_elf()
source=(
    '#include "recomp/rc.h"\n'
    'static const RcFunction table[] = {\n'
    + "\n".join(
        "    {%s, %d, %sull, f_%x, &d_%x},"%
        (f["offset"],f["size"],f["expected_hash"],
         int(f["offset"],16),int(f["offset"],16))
        for f in fixture["functions"]
    )+"\n};\n"
)
verified=v.verify(fixture,image,source)
assert len(verified)==7
assert all(v.fnv1a64(bytes.fromhex(f["code_hex"]))==item["hash"]
           for f,item in zip(fixture["functions"],verified))
header=v.render(verified)
assert header.count("UINT64_C(0x")==14 and (
    "shyt_v400_expected[]" in header)
for i in range(12):
    source_mutated=source
    image_mutated=image
    fixture_mutated=copy.deepcopy(fixture)
    if i==0:source_mutated=source.replace(
        "0xcaf2b035bd6212e7ull","0xcaf2b035bd6212e6ull")
    if i==1:source_mutated=source.replace(
        "{0x1000, 6,","{0x1000, 5,")
    if i==2:source_mutated=source.replace(
        "f_1000, &d_1000","f_1000, &d_1001")
    if i==3:source_mutated=source.replace(
        "f_10c0, &d_10c0","f_10a0, &d_10c0")
    if i==4:source_mutated=source.replace(
        "{0x10c0, 3,","{0x10c1, 3,")
    if i==5:source_mutated=source.replace(
        "static const RcFunction table[]","static const unsigned table[]")
    if i==6:source_mutated=source.replace(
        "{0x10c0, 3, 0xfa30281be4fbf37bull, f_10c0, &d_10c0},","")
    if i==7:image_mutated=image[:0x10a0]+b"\x90"+image[0x10a1:]
    if i==8:fixture_mutated["functions"][0]["expected_hash"]="0xcaf2b035bd6212e6"
    if i==9:fixture_mutated["functions"][0]["code_hex"]="f0480fb13790"
    if i==10:fixture_mutated["functions"]=fixture_mutated["functions"][:6]
    if i==11:fixture_mutated["upstream_revision"]="untrusted"
    if i<8:
        try:v.verify(fixture_mutated,image_mutated,source_mutated)
        except ValueError:pass
        else:raise AssertionError(f"compiler/image identity drift accepted: {i}")
    else:
        with TemporaryDirectory() as temp:
            path=Path(temp)/"id.json"
            path.write_text(json.dumps(fixture_mutated),encoding="utf-8")
            try:v.load_fixture(path)
            except ValueError:pass
            else:raise AssertionError(f"independent function fixture changed: {i}")

print("NATIVE_V400_INDEPENDENT_FUNCTION_IDENTITY_NEGATIVE_TESTS_PASS")
