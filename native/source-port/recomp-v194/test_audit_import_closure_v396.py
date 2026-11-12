#!/usr/bin/env python3
"""V396: negative fixtures for strict manifest/source/target/return closure."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
p=Path(__file__).with_name("audit_import_closure_v396.py")
spec=importlib.util.spec_from_file_location("native_v396_manifest",p)
assert spec and spec.loader
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
manifest=v.load_manifest(p.with_name("native_import_manifest_fixture_v396.json"),"invented-test-only")
names=[f"f_{v.number(x):x}" for x in manifest["function_offsets"]]
table="#include \"recomp/rc.h\"\n"+"\n".join(
    f"void {n}(BbCpu *c);" for n in names)+"\n"+
    "const RcFunction *bb_recomp_init(const RcApi *a,size_t *n){\n"+
    "\n".join(f"  (void)&d_{name[2:]};" for name in names)+"\n return 0;\n}\n"
shard='#include "recomp/rc.h"\n'
for name in names:
    if name=="f_10a0":
        body="  rc->call(c,c->r[RAX],B + 0x10a2ull);\n"
    elif name=="f_10c0":
        body="  rc->call(c,c->r[RAX],B + 0x10c2ull);\n"
    else:
        body="  c->r[RAX]=c->r[RDI];\n"
    shard+=f"void {name}(BbCpu *c) {{\n"+body+"}\n"
ok=v.verify(manifest,manifest["image_sha256"],table,[shard])
assert ok["functions"]==7 and ok["import_calls"]==2
assert ok["image_fingerprint_verified"] and not ok["original_game_boot_proven"]
h=v.render_header(manifest)
assert "SHYT_V396_SITE_COUNT" in h and "0x4010c2" in h
for mode in range(11):
    other=copy.deepcopy(manifest)
    t=table; s=shard; image=manifest["image_sha256"]
    if mode==0:image="0"*64
    if mode==1:other["function_offsets"]=other["function_offsets"][:-1]
    if mode==2:other["calls"]=other["calls"][:-1]
    if mode==3:other["calls"][1]["next_offset"]="0x10c3"
    if mode==4:other["calls"][1]["guest_target"]=other["calls"][0]["guest_target"]
    if mode==5:other["calls"][0]["function_offset"]="0x1020"
    if mode==6:t=t.replace("void f_10c0(BbCpu *c);","")
    if mode==7:s=s.replace("rc->call(c,c->r[RAX],B + 0x10c2ull);","rc->step(c);")
    if mode==8:s=s.replace("rc->call(c,c->r[RAX],B + 0x10c2ull);","rc->call(c,c->r[RAX],c->r[RCX]);")
    if mode==9:s=s.replace("void f_10c0(BbCpu *c) {","void f_10ff(BbCpu *c) {")
    if mode==10:other["calls"].append(copy.deepcopy(other["calls"][0]))
    try:v.verify(other,image,t,[s])
    except ValueError:pass
    else:raise AssertionError(f"unclosed import or source drift accepted: {mode}")
for mode in range(8):
    other=copy.deepcopy(manifest)
    if mode==0:other["calls"][0]["guest_target"]="0x0"
    if mode==1:other["calls"][0]["constant"]="0x2"
    if mode==2:other["calls"][0]["service"]="execute_guest_fallback"
    if mode==3:other["calls"][1]["recover_code"]=True
    if mode==4:other["calls"][0]["next_offset"]="0x10A2"
    if mode==5:other["upstream_revision"]="unknown"
    if mode==6:other["scope"]="owner-private"
    if mode==7:other["image_sha256"]="0"*64
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as t:
        q=Path(t)/"manifest.json"
        q.write_text(json.dumps(other),encoding="utf-8")
        try:v.load_manifest(q,"invented-test-only")
        except ValueError:pass
        else:raise AssertionError(f"malformed or unauthorized native manifest accepted: {mode}")
print("NATIVE_V396_IMPORT_CLOSURE_MANIFEST_NEGATIVE_TESTS_PASS")
