#!/usr/bin/env python3
"""V395: reject original-free malformed second CALL site / source mutation."""
from pathlib import Path
import importlib.util
p=Path(__file__).with_name("verify_generated_import_v395.py")
spec=importlib.util.spec_from_file_location("v395audit",p)
assert spec and spec.loader
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
instrument=importlib.util.spec_from_file_location(
    "v390instrument",p.with_name("instrument_generated_aot_memory_v390.py"))
v=importlib.util.module_from_spec(instrument);instrument.loader.exec_module(v)
source='''#include "recomp/rc.h"
void f_10a0(BbCpu *c) {
 rc->call(c,c->r[RAX], B + 0x10a2ull);
}
void f_10c0(BbCpu *c) {
 rc->call(c,c->r[RAX], B + 0x10c2ull);
}
void f_1000(BbCpu *c) {
 rc_st(c->r[RSP],8,rc_ld(c->r[RDI],8));
}
'''
patched,_=v.transform(source)
a.inspect_source(source,patched)
for orig,pt in (
 (source.replace("0x10c2ull","0x10a2ull"),patched.replace("0x10c2ull","0x10a2ull")),
 (source.replace("rc->call(c,c->r[RAX], B + 0x10c2ull)",
                 "rc->step(c)"),patched.replace(
                 "rc->call(c,c->r[RAX], B + 0x10c2ull)","rc->step(c)")),
 (source.replace("void f_10c0(BbCpu *c)","void f_10c1(BbCpu *c)"),
  patched.replace("void f_10c0(BbCpu *c)","void f_10c1(BbCpu *c)")),
 (source,patched+"\n/* untrusted source drift */"),
):
    try:a.inspect_source(orig,pt)
    except ValueError:pass
    else:raise AssertionError("unverified generated return site accepted")
print("NATIVE_V395_GENERATED_IMPORT_AUDIT_NEGATIVE_TESTS_PASS")
