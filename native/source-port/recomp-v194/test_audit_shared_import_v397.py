#!/usr/bin/env python3
"""V397 strict multi-caller one-import manifest: source/ABI negative cases."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
p=Path(__file__).with_name("audit_import_closure_v396.py")
spec=importlib.util.spec_from_file_location("native_v397_shared",p)
assert spec and spec.loader
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
m=v.load_manifest(p.with_name("native_shared_import_manifest_fixture_v397.json"),"invented-test-only")
assert m["calls"][0]["guest_target"]==m["calls"][1]["guest_target"]
names=[f"f_{v.number(x):x}" for x in m["function_offsets"]]
table=('#include "recomp/rc.h"\n'+
       "\n".join(f"void {n}(BbCpu *c);" for n in names)+
       "\nconst RcFunction *bb_recomp_init(const RcApi *a,size_t *n){\n"+
       "\n".join(f"  (void)&d_{name[2:]};" for name in names)+
       "\n return 0;\n}\n")
shard='#include "recomp/rc.h"\n'
for n in names:
    body=("rc->call(c,c->r[RAX],B + 0x10a2ull);" if n=="f_10a0" else
          "rc->call(c,c->r[RAX],B + 0x10c2ull);" if n=="f_10c0" else
          "c->r[RAX]=c->r[RDI];")
    shard+=f"void {n}(BbCpu *c) {{\n {body}\n}}\n"
status=v.verify(m,m["image_sha256"],table,[shard],allow_shared_targets=True)
assert status["functions"]==7 and status["import_calls"]==2
assert status["distinct_import_targets"]==1 and status["shared_target_provenance"]
try:v.verify(m,m["image_sha256"],table,[shard])
except ValueError:pass
else:raise AssertionError("V396 strict single-target manifest unexpectedly accepted shared import")
header=v.render_header(m)
assert header.count("UINT64_C(0x40009100)")==2
assert "UINT64_C(0x4010a2)" in header and "UINT64_C(0x4010c2)" in header
for mode in range(13):
    x=copy.deepcopy(m)
    t=table;s=shard;hash=m["image_sha256"]
    if mode==0:x["calls"][1]["service"]="return_constant"
    if mode==1:x["calls"][1]["constant"]="0x3"
    if mode==2:x["calls"][1]["recover_code"]=671
    if mode==3:x["calls"][1]["next_offset"]="0x10c3"
    if mode==4:x["calls"][0]["next_offset"]="0x10c2"
    if mode==5:x["calls"].append(copy.deepcopy(x["calls"][1]))
    if mode==6:x["calls"]=x["calls"][:1]
    if mode==7:hash="0"*64
    if mode==8:t=t.replace("void f_10c0(BbCpu *c);","")
    if mode==9:s=s.replace("B + 0x10c2ull","B + 0x10c3ull")
    if mode==10:s=s.replace("rc->call(c,c->r[RAX],B + 0x10c2ull);","rc->step(c);")
    if mode==11:s=s.replace("void f_10c0(BbCpu *c) {","void f_10ff(BbCpu *c) {")
    if mode==12:x["function_offsets"]=x["function_offsets"][:-1]
    try:v.verify(x,hash,t,[s],allow_shared_targets=True)
    except ValueError:pass
    else:raise AssertionError(f"unsafe shared import manifest accepted: {mode}")
for mode in range(6):
    x=copy.deepcopy(m)
    if mode==0:x["calls"][1]["service"]="unknown"
    if mode==1:x["calls"][1]["constant"]="0x1"
    if mode==2:x["calls"][1]["recover_code"]=True
    if mode==3:x["calls"][0]["guest_target"]="0x0"
    if mode==4:x["scope"]="owner-private"
    if mode==5:x["upstream_revision"]="unverified"
    with TemporaryDirectory() as tmp:
        file=Path(tmp)/"manifest.json"
        file.write_text(json.dumps(x),encoding="utf-8")
        try:v.load_manifest(file,"invented-test-only")
        except ValueError:pass
        else:raise AssertionError(f"malformed shared target accepted: {mode}")
print("NATIVE_V397_SHARED_IMPORT_MANIFEST_NEGATIVE_TESTS_PASS")
