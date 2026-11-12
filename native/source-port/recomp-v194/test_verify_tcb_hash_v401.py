#!/usr/bin/env python3
"""V401: negative controls for exact independently decoded TCB load hashes."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json

ROOT=Path(__file__).resolve().parent
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
v=load("v401verify","verify_tcb_hash_v401.py")
g=load("v401generate","generate_tcb_probe_v401.py")
m=v.load_manifest(ROOT/"native_tcb_hash_fixture_v401.json")
image=g.build_elf()
source=('static const RcFunction table[] = {\n'+
    '\n'.join('    {%s, %d, %sull, f_%x, &d_%x},'%
        (item['offset'],item['size'],item['expected_hash'],
         int(item['offset'],16),int(item['offset'],16))
        for item in m['functions'])+'\n};\n')
shard=""
for item in m["functions"]:
    off=item["offset"][2:]
    body=("c->tcb;" if item["hash_mode"].startswith("tcb_") else
          "rc->step(c);" if item["hash_mode"]=="raw_fs_nonzero" else
          "c->r[0]=0;")
    shard+=f"void f_{off}(BbCpu *c) {{ {body} }}\n"
status=v.verify(m,image,source,shard)
assert status["compiled_functions"]==12 and status["direct_tcb_functions"]==4
assert v.canonical_hash(bytes.fromhex(v.FS_MOV_RAX0),"tcb_rax_fs0")==(
       v.canonical_hash(bytes.fromhex(v.GS_MOV_RAX40),"tcb_rax_gs40"))
assert v.canonical_hash(bytes.fromhex(v.FS_MOV_RBX0),"tcb_rbx_fs0")==(
       v.canonical_hash(bytes.fromhex(v.GS_MOV_RBX40),"tcb_rbx_gs40"))
assert v.canonical_hash(bytes.fromhex(v.FS_MOV_RAX40),"raw_fs_nonzero")!=(
       v.canonical_hash(bytes.fromhex(v.FS_MOV_RAX0),"tcb_rax_fs0"))
# Do not normalize a GS instruction by accident as FS or accept wrong
# destination register, displacement or decoder boundaries.
for code,mode in (
 (bytes.fromhex(v.FS_MOV_RAX40),"tcb_rax_fs0"),
 (bytes.fromhex(v.GS_MOV_RAX40),"tcb_rbx_gs40"),
 (bytes.fromhex(v.FS_MOV_RBX0),"tcb_rax_fs0"),
 (bytes.fromhex(v.FS_MOV_RAX0)[:-1]+b"\x90","tcb_rax_fs0"),
 (bytes.fromhex(v.FS_MOV_RAX0)[:-2],"tcb_rax_fs0"),
):
    try:v.canonical_hash(code,mode)
    except ValueError:pass
    else:raise AssertionError("invalid decoded TCB instruction accepted")
for mode in range(8):
    source_mut=source
    body_mut=shard
    image_mut=image
    if mode==0: source_mut=source.replace("0xa2827e1bb306bdc9ull","0x123456789ull",1)
    if mode==1: source_mut=source.replace("{0x10e0, 10,","{0x10e0, 9,")
    if mode==2: source_mut=source.replace("f_10e0, &d_10e0","f_10e0, &d_10e1")
    if mode==3: source_mut=source.replace("f_1160, &d_1160","f_1120, &d_1160")
    if mode==4: source_mut=source.replace("{0x1160, 10,","{0x1161, 10,")
    if mode==5: body_mut=shard.replace("void f_10e0(BbCpu *c) { c->tcb; }",
                                   "void f_10e0(BbCpu *c) { rc->step(c); }")
    if mode==6: body_mut=shard.replace("void f_1140(BbCpu *c) { rc->step(c); }",
                                   "void f_1140(BbCpu *c) { c->tcb; }")
    if mode==7: image_mut=image[:0x1100]+b"\x90"+image[0x1101:]
    try:v.verify(m,image_mut,source_mut,body_mut)
    except ValueError:pass
    else:raise AssertionError(f"untrusted generated TCB hash or source {mode}")
for change in ("functions","image_sha256","upstream_bbcpu_recomp_git_blob",
               "upstream_bbcpu_decode_git_blob"):
    altered=json.loads(json.dumps(m))
    if change=="functions": altered[change][8]["expected_hash"]="0xa2827e1bb306bdca"
    else:altered[change]="0"*40
    with TemporaryDirectory() as tmp:
        p=Path(tmp)/"manifest.json"
        p.write_text(json.dumps(altered),encoding="utf-8")
        try:v.load_manifest(p)
        except ValueError:pass
        else:raise AssertionError("untrusted manifest accepted: "+change)
print("NATIVE_V401_TCB_DECODE_HASH_NEGATIVE_TESTS_PASS")
