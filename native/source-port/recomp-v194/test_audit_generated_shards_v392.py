#!/usr/bin/env python3
"""V392: bounded positive/negative generated C shard inventory regression."""
from __future__ import annotations
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("audit_generated_shards_v392.py")
spec=importlib.util.spec_from_file_location("v392_audit",p)
assert spec and spec.loader
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
original='''#include "recomp/rc.h"
void f_1000(BbCpu *c) {
  uint64_t x = rc_ld(c->r[RDI],8);
  uint64_t seen=0;
  rc_cas(c->r[RDI],8,x,x,&seen);
  BbVec a=rc_vld(c->r[RSI],16);
  BbVec b=rc_vld(c->r[RSI],32);
  rc_vst(c->r[RSP],16,a);
  rc_vst(c->r[RSP],32,b);
}
void f_1020(BbCpu *c) {
  rc_st(c->r[RDI],8,rc_ld(c->r[RSI],8));
}
'''
table='''#include "recomp/rc.h"
void f_1000(BbCpu *c);
void f_1020(BbCpu *c);
const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {
  (void)api;(void)count;static RcFn *a=&d_1000,*b=&d_1020;
  (void)a;(void)b;return 0;
}
'''
overlay,_=audit.v390.transform(original)
result=audit.audit(table,[(original,overlay)],2)
assert result["generated_functions"]==2
assert result["instrumented_shards"]==1
assert result["actual_memory_helper_calls"]["rc_cas"]==1
for bad_table,bad_shards,bad_count in (
    (table,[(original,overlay+"\n/* unexpected diff */")],2),
    (table,[(original.replace("rc_ld(","bb_load("),overlay)],2),
    (table.replace("void f_1020(BbCpu *c);",""),[(original,overlay)],2),
    (table,[(original,overlay)],3),
    (table,[(original,overlay),(original,overlay)],2),
    (table.replace("&d_1020","&d_1000"),[(original,overlay)],2),
    (table,[(original.replace("rc_cas(","rc_ld("),
             overlay.replace("rc_cas(","rc_ld("))],2),
):
    try:
        audit.audit(bad_table,bad_shards,bad_count)
    except ValueError:
        pass
    else:
        raise AssertionError("V392 audit improperly accepted an unsafe shard")
print("NATIVE_V392_AOT_INVENTORY_NEGATIVE_TESTS_PASS")
