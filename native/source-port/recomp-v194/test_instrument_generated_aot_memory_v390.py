#!/usr/bin/env python3
"""Original-free negative/positive tests for the pinned V390 generated-C gate."""
from __future__ import annotations
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("instrument_generated_aot_memory_v390.py")
spec=importlib.util.spec_from_file_location("v390_instrument",path)
assert spec and spec.loader
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

valid='''#include "recomp/rc.h"
void invented_function(BbCpu *c) {
    const uint64_t a = rc_ld(c->r[RDI], 8);
    rc_sts(c->r[RSP], 8, a);
    const uint64_t v = rc_lds(c->r[RSP],8);
    rc_st(c->r[RDI],8,v);
    uint64_t seen=0;
    rc_cas(c->r[RDI],8,v,v,&seen);
    BbVec vv=rc_vld(c->r[RDI],16);
    rc_vst(c->r[RDI],16,vv);
}
'''
done,counts=module.transform(valid,True)
assert done.count('#include "native_generated_memory_calls_v390.h"')==1
assert counts=={"rc_ld":1,"rc_lds":1,"rc_st":1,"rc_sts":1,
                "rc_cas":1,"rc_vld":1,"rc_vst":1}
assert done.index('#include "recomp/rc.h"')<done.index(
       '#include "native_generated_memory_calls_v390.h"')
for bad in (
    valid.replace('#include "recomp/rc.h"',''),
    valid.replace('#include "recomp/rc.h"','#include "recomp/rc.h"\n#include "recomp/rc.h"'),
    valid.replace('rc_ld(','bb_load('),
    valid.replace('rc_st(','bb_store('),
    valid.replace('#include "recomp/rc.h"',
                  '#include "recomp/rc.h"\n#include "native_generated_memory_calls_v390.h"'),
    '''#include "recomp/rc.h"
void noop(BbCpu *c) { c->r[0]=1; }
''',
):
    try:module.transform(bad)
    except ValueError:pass
    else:raise AssertionError("unsafe/malformed generated source was accepted")
try:module.transform(valid.replace('rc_sts(c->r[RSP], 8, a);',''),
                     require_scalar=True)
except ValueError:
    # There is still rc_st, so this should NOT fail. Test intentionally
    # rejects incorrectly demanding both stack and general writers.
    raise AssertionError("misidentified mixed-store code")
print("NATIVE_V390_SOURCE_LOCKED_INSTRUMENTATION_NEGATIVE_TESTS_PASS")
