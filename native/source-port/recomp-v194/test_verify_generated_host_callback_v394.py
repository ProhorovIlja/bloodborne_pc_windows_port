#!/usr/bin/env python3
"""V394: negative tests for six-function compiled object and RcApi.call source."""
from __future__ import annotations
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("verify_generated_host_callback_v394.py")
s=importlib.util.spec_from_file_location("v394auditor",p)
assert s and s.loader
v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
src='''#include "recomp/rc.h"
void f_10a0(BbCpu *c) {
  uint64_t t=c->r[RAX];
  rc->call(c,t,B + 0x10a2ull);
}
void f_1000(BbCpu *c) { rc_st(c->r[RSP],8,rc_ld(c->r[RDI],8)); }
'''
spec=importlib.util.spec_from_file_location("v390audit",
    p.with_name("instrument_generated_aot_memory_v390.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
overlay,_=m.transform(src)
v.verify_call_source(src,overlay)
for bad,patched in (
    (src.replace("rc->call(","rc->tail("),overlay.replace("rc->call(","rc->tail(")),
    (src,overlay+"\n/* appended untrusted bytes */"),
    (src.replace("void f_10a0","void f_10ff"),
     overlay.replace("void f_10a0","void f_10ff")),
    (src.replace("rc->call(c,t,B + 0x10a2ull)","rc->step(c)"),
     overlay.replace("rc->call(c,t,B + 0x10a2ull)","rc->step(c)"))
):
    try:v.verify_call_source(bad,patched)
    except ValueError:pass
    else:raise AssertionError("unsafe real generated callback source accepted")
original=v.original
unset="\n".join(" U "+x for x in original.PRESENT)
defs="\n".join(f"00000000000000{i:02x} T {name}" for i,name in enumerate(v.FUNCTIONS))
refs="\n".join(f"000000000000000{i} R_X86_64_PLT32 {name}-0x4" for i,name in enumerate(original.PRESENT))
prev=original.FUNCTIONS
try:
    original.FUNCTIONS=v.FUNCTIONS
    original.verify_symbols(unset,defs,refs)
    for u,d,r in [
        (unset,defs.replace("f_10a0","f_10ff"),refs),
        (unset.replace(original.PRESENT[0],""),defs,refs),
        (unset,defs,refs.replace(original.PRESENT[2],"")),
        (unset+"\n U bbcpu_step",defs,refs)
    ]:
        try:original.verify_symbols(u,d,r)
        except ValueError:pass
        else:raise AssertionError("missing V390 bridge or sixth native call accepted")
finally:
    original.FUNCTIONS=prev
print("NATIVE_V394_GENERATED_CALL_OBJECT_NEGATIVE_TESTS_PASS")
