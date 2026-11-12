#!/usr/bin/env python3
"""Negative and positive V403 admission tests: original-free inputs only."""
from __future__ import annotations

import copy

import native_route_attestation_v403 as v403

v401 = v403.v402.module("v403_fixture", "verify_tcb_hash_v401.py")
v396 = v403.v402.module("v403_calls", "audit_import_closure_v396.py")
fixture = [row for row in v401.EXPECTED if row[0] != "0x1140"]
manifest = v396.load_manifest(
    v403.ROOT / "native_11_function_import_manifest_v402.json",
    "invented-test-only"
)
ledger = {
    "generated_source_functions": 12,
    "quarantined_fallbacks": {"0x1140": ["rc->step"]},
    "native_only_functions": 11,
    "failclosed_guest_bail_tail_edges": 22,
    "native_indirect_call_sites": 2,
    "runtime_original_game_proven": False
}


def table(rows):
    parts = ['#include "recomp/rc.h"\n']
    parts.extend("void f_%x(BbCpu *c);\n" % int(o, 16)
                 for o, _, _, _ in rows)
    parts.append("static const RcFunction table[] = {\n")
    parts.extend(" {%s, %d, %sull, f_%x, &d_%x},\n" %
                 (o, len(bytes.fromhex(code)), h, int(o, 16), int(o, 16))
                 for o, code, _, h in rows)
    parts.append("};\nconst RcFunction *bb_recomp_init("
                 "const RcApi *api, size_t *count) { return table; }\n")
    return "".join(parts)


def shard(rows):
    chunks = ['#include "recomp/rc.h"\n']
    for o, _, _, _ in rows:
        n = int(o, 16)
        action = ("rc->call(c,c->r[RAX],B + 0x%xull);" % (n + 2)
                  if n in (0x10a0, 0x10c0) else "c->r[RAX] = 0;")
        chunks.append(
            "void f_%x(BbCpu *c) {\n%s\n" % (n, action) +
            "if (0) rc->bail(c, entry_rsp);\n"
            "if (0) rc->tail(c);\n}\n"
        )
    return "".join(chunks)


t = table(fixture)
s = shard(fixture)
report = v403.classify(manifest, ledger, t, s)
assert report["compiled_candidate_count"] == 11
assert report["excluded_step_function"] == "0x1140"
assert not report["full_guest_call_graph_closed"]
assert not report["original_game_native_entry_proven"]
assert not report["native_runtime_dispatch_wired"]
assert len(report["functions"]) == 11
assert len(report["host_import_edges"]) == 2
assert sum(x["typed_host_import_sites"] for x in report["functions"]) == 2
assert all(not x["game_runtime_entry_proven"] for x in report["functions"])
assert all(x["unhandled_transfer_policy"] == "abort" for x in report["functions"])
hdr = v403.header(report)
assert "0x1140" not in hdr
assert "shyt_v403_is_synthetic_candidate" in hdr

def refused(m=manifest, l=ledger, tbl=t, sh=s):
    try:
        v403.classify(m, l, tbl, sh)
    except (ValueError, KeyError, TypeError):
        return
    raise AssertionError("V403 accepted an unattested synthetic route mutation")


for change in (
    lambda x: x.update(native_only_functions=12),
    lambda x: x.update(runtime_original_game_proven=True),
    lambda x: x.update(failclosed_guest_bail_tail_edges=21),
    lambda x: x.update(quarantined_fallbacks={}),
    lambda x: x.update(full_guest_call_graph_closed=True),
):
    bad = copy.deepcopy(ledger)
    change(bad)
    refused(l=bad)

bad = copy.deepcopy(manifest)
bad["function_offsets"] = bad["function_offsets"][:-1]
refused(m=bad)
bad = copy.deepcopy(manifest)
bad["calls"].append(dict(bad["calls"][0]))
refused(m=bad)
bad = copy.deepcopy(manifest)
bad["image_sha256"] = "0" * 64
refused(m=bad)
bad = copy.deepcopy(manifest)
bad["calls"][0]["function_offset"] = "0x1000"
refused(m=bad)

refused(tbl=t.replace("f_1160, &d_1160", "f_1140, &d_1140"))
refused(sh=s.replace("void f_1160(", "void f_1140("))
refused(sh=s.replace("c->r[RAX] = 0;", "rc->step(c);", 1))
refused(sh=s.replace("c->r[RAX] = 0;", "f_ffff(c);", 1))
refused(sh=s.replace("rc->tail(c);", "rc->tail(z);", 1))
refused(sh=s.replace("rc->bail(c, entry_rsp);", "c->r[RAX] = 0;", 1))
refused(sh=s.replace("rc->call(c,c->r[RAX],B + 0x10a2ull);",
                       "c->r[RAX] = 0;", 1))
print("NATIVE_V403_SYNTHETIC_ROUTE_NEGATIVE_TESTS_PASS")
