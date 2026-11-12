#!/usr/bin/env python3
"""V402 strict native-only set provenance: no translator/STEP leakage."""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def imp(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/filename)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
audit=imp("v402_audit","audit_native_only_v402.py")
probe=imp("v401_probe","generate_tcb_probe_v401.py")
hashver=imp("v401_hash","verify_tcb_hash_v401.py")
sitever=imp("v396_audit","audit_import_closure_v396.py")
manifest=sitever.load_manifest(
    ROOT/"native_11_function_import_manifest_v402.json","invented-test-only")
fullimage=probe.build_elf()
nativeimage=probe.build_elf(native_only=True)
assert len(nativeimage)==len(fullimage)==0x1200
assert fullimage!=nativeimage
orig=hashver.EXPECTED

def code(off,mode):
    if mode.startswith("tcb_"): return "c->r[0] = c->tcb;"
    if mode=="raw_fs_nonzero":return "rc->step(c);"
    if off=="0x10a0":return "rc->call(c,c->r[RAX],B + 0x10a2ull);"
    if off=="0x10c0":return "rc->call(c,c->r[RAX],B + 0x10c2ull);"
    return "c->r[RAX] = 0;"
def table(rows):
    return ('#include "recomp/rc.h"\n'+
        ''.join(f"void f_{int(o,16):x}(BbCpu *c);\n" for o,_,_,_ in rows)+
        'static const RcFunction table[] = {\n'+
        ''.join("    {%s, %d, %sull, f_%x, &d_%x},\n"%
                (o,len(bytes.fromhex(codebytes)),hashval,int(o,16),int(o,16))
                for o,codebytes,mode,hashval in rows)+
        '};\nconst RcFunction *bb_recomp_init(const RcApi *api,size_t *count) { return table; }\n')
def shard(rows):
    return '#include "recomp/rc.h"\n'+''.join(
        f"void f_{int(o,16):x}(BbCpu *c) {{\n {code(o,mode)}\n"
        " if (0) rc->bail(c, entry_rsp);\n if (0) rc->tail(c);\n}\n"
        for o,_,mode,_ in rows)
full_table=table(orig);full_shard=shard(orig)
allowed=[r for r in orig if r[0]!="0x1140"]
native_table=table(allowed);native_shard=shard(allowed)
result=audit.evaluate(full_table,full_shard,fullimage,
                      native_table,native_shard,nativeimage,manifest)
assert result["generated_source_functions"]==12
assert result["native_only_functions"]==11
assert result["quarantined_fallbacks"]=={"0x1140":["rc->step"]}
assert result["native_indirect_call_sites"]==2
overlay=imp("v402_native_overlay","native_failclosed_overlay_v402.py")
instrumented=native_shard.replace('#include "recomp/rc.h"',
    '#include "recomp/rc.h"\n#include "native_generated_memory_calls_v390.h"',1)
compiled,counts=overlay.transform(instrumented)
assert counts["functions"]==11 and counts["source_imports"]==2
assert counts["bail_abort"]==11 and counts["tail_abort"]==11
assert "rc->bail(" not in compiled and "rc->tail(" not in compiled
assert "#include <stdlib.h>" in compiled
for poisoned in (
    instrumented.replace("rc->tail(c);","rc->tail(cpu);",1),
    instrumented.replace("rc->bail(c, entry_rsp);","rc->bail(c,0);",1),
    instrumented.replace("c->r[RAX] = 0;","rc->step(c);",1),
    instrumented.replace("c->r[RAX] = 0;","rc->trace(0,c->r,c);",1),
    instrumented.replace("c->r[RAX] = 0;","rc->unknown(c);",1),
    instrumented.replace("void f_1160","void f_1140"),
):
    try:overlay.transform(poisoned)
    except ValueError:pass
    else:raise AssertionError("unsafe source original-only fallback overlay accepted")

cases=[
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("void f_1160","void f_1140"),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("c->r[RAX] = 0;","rc->step(c);",1),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("c->r[RAX] = 0;","rc->bail(c,0);",1),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("c->r[RAX] = 0;","rc->tail(c);",1),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("c->r[RAX] = 0;","rc->trace(1,c->r,c);",1),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("c->r[RAX] = 0;","rc->unknown(c);",1),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("B + 0x10c2ull","B + 0x10c3ull"),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("c->r[RAX] = 0;","bb_load(c,1);",1),nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,
     native_shard.replace("void f_1160(BbCpu *c) {\n c->r[0] = c->tcb;\n}",""),nativeimage,manifest),
    (full_table,full_shard.replace("rc->step(c);","c->r[RAX] = 0;"),
     fullimage,native_table,native_shard,nativeimage,manifest),
    (full_table,full_shard.replace("rc->step(c);","rc->bail(c,0);"),
     fullimage,native_table,native_shard,nativeimage,manifest),
    (full_table,full_shard,fullimage,native_table,native_shard,
     fullimage,manifest),
    (full_table,full_shard,fullimage,native_table.replace(
        "{0x10e0, 10,","{0x10e0, 9,"),native_shard,nativeimage,manifest),
]
altered=copy.deepcopy(manifest);altered["function_offsets"]=altered["function_offsets"][:-1]
cases.append((full_table,full_shard,fullimage,
              native_table,native_shard,nativeimage,altered))
altered=copy.deepcopy(manifest);altered["calls"]=altered["calls"][:1]
cases.append((full_table,full_shard,fullimage,
              native_table,native_shard,nativeimage,altered))
for i,inputs in enumerate(cases):
    try:audit.evaluate(*inputs)
    except ValueError:pass
    else:raise AssertionError(f"unsafe native AOT closure accepted mode={i}")
print("NATIVE_V402_FALLBACK_LEDGER_AND_NATIVE_ONLY_NEGATIVE_TESTS_PASS")
