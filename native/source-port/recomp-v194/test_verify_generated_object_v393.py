#!/usr/bin/env python3
"""Negative verifier fixtures do not process or publish game source."""
from __future__ import annotations
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("verify_generated_object_v393.py")
sp=importlib.util.spec_from_file_location("v393obj",p)
assert sp and sp.loader
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
present=m.PRESENT
undef="\n".join(" U "+x for x in present)
defined="\n".join(f"00000000000000{i:02x} T {name}" for i,name in enumerate(m.FUNCTIONS))
relocs="\n".join(f"000000000000000{i} R_X86_64_PLT32 {name}-0x4" for i,name in enumerate(present))
m.verify_symbols(undef,defined,relocs)
for u,d,r in (
    (undef.replace(present[0],""),defined,relocs),
    (undef,defined,relocs.replace(present[1],"")),
    (undef,defined.replace("f_1060","f_bad"),relocs),
    (undef+"\n U bbcpu_step",defined,relocs),
    (undef,defined,relocs+"\n U bbcpu_jit_run"),
    (undef+"\n U bb_load",defined,relocs)
):
    try:m.verify_symbols(u,d,r)
    except ValueError:pass
    else:raise AssertionError("unsafe compiled object provenance was accepted")
print("NATIVE_V393_ELF_OBJECT_AUDIT_NEGATIVE_TESTS_PASS")
