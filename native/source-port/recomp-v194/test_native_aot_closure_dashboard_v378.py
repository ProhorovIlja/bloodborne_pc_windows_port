#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic aggregate testing, not a native original-game AOT proof."""
import json
from pathlib import Path
import tempfile
from native_aot_closure_dashboard_v378 import InvalidEvidence, bounded, report


def refused(f):
    try:
        f()
    except InvalidEvidence:
        return
    raise AssertionError("unsafe aggregate evidence accepted")


def main():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        cov = {"functions_scanned": 20, "aot_functions_registered": 18,
               "functions_not_in_aot_table": 2,
               "complete_scanner_to_aot_registration": False,
               "private_game_symbol": "DO_NOT_DISCLOSE", "private_address": "0xDEADBEEF"}
        coff = {"verified_amd64_coff_objects": 3,
                "external_references_unresolved_in_game_objects": 2,
                "object_modules_blocked_by_host_imports": 2,
                "native_pe_link_complete": False,
                "guest_runtime_removed": False,
                "secret_export": "RETAIL_ORIGINAL_NAME"}
        p = folder / "coverage.json"
        c = folder / "coff.json"
        p.write_text(json.dumps(cov))
        c.write_text(json.dumps(coff))
        out = report(bounded(p), bounded(c))
        blob = json.dumps(out)
        assert out["functions_absent_from_aot"] == 2
        assert out["external_names_unresolved_in_game_objects"] == 2
        assert not out["strict_native_game_ready"]
        assert "original_functions_missing_from_aot" in out["blockers"]
        assert "DO_NOT_DISCLOSE" not in blob
        assert "RETAIL_ORIGINAL_NAME" not in blob
        assert "0xDEADBEEF" not in blob
        zero = dict(cov, aot_functions_registered=20,
                    functions_not_in_aot_table=0,
                    complete_scanner_to_aot_registration=True)
        linked = dict(coff, external_references_unresolved_in_game_objects=0,
                      object_modules_blocked_by_host_imports=0)
        good = report(zero, linked)
        assert good["strict_native_game_ready"] is False
        assert "original_native_game_pe_and_elf_link_unproven" in good["blockers"]
        missing = report(None, None)
        assert len(missing["blockers"]) >= 5
        for bad in (dict(cov, functions_scanned=10),
                    dict(cov, complete_scanner_to_aot_registration=True),
                    dict(cov, functions_scanned=True),
                    dict(cov, functions_not_in_aot_table=-1)):
            refused(lambda bad=bad:report(bad, coff))
        for bad in (dict(coff, verified_amd64_coff_objects=0),
                    dict(coff, object_modules_blocked_by_host_imports=4),
                    dict(coff, native_pe_link_complete=True),
                    dict(coff, object_modules_blocked_by_host_imports=0)):
            refused(lambda bad=bad:report(cov, bad))
        p.write_text("{" + "a"*32800)
        refused(lambda:bounded(p))
        p.unlink()
        p.symlink_to(c)
        refused(lambda:bounded(p))
    print("NATIVE_V378_PRIVACY_SAFE_AOT_COFF_GAP_GATES_PASS")


if __name__ == "__main__":
    main()
