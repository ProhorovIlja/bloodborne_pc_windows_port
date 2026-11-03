#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V335: synthetic-only exact original ELF attestation / private manifest tests.

Never use, copy, hash or upload game content in public CI. Positive matching
case stubs the one private input digest, to prove pipeline state propagation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from unittest.mock import patch

import prepare_private_full_game_v204 as prep


def exercise(fake_matching_input: bool, drift: bool = False) -> None:
    with tempfile.TemporaryDirectory(prefix="fictional-aot-v335-") as tmp:
        base = Path(tmp)
        source = base / "synthetic.elf"
        # 1 MiB+ entirely invented image, enough for the size and magic fence.
        source.write_bytes(b"\x7fELF" + b"x" * 1_099_996)
        root = base / "fake-public-tools"
        (root / "annotations").mkdir(parents=True)
        (root / "annotations/functions.tsv").write_text("synthetic\n")
        work = base / "private-output"
        expected = prep.ORIGINAL_109_SHA256
        ordinary = prep.sha(source)
        assert ordinary != expected
        assert not prep.verified_original_109_digest(ordinary)
        assert prep.verified_original_109_digest(expected)
        assert not prep.verified_original_109_digest(expected.upper())
        assert not prep.verified_original_109_digest(None)
        original_sha = prep.sha
        seen = 0

        def controlled_sha(path: Path) -> str:
            nonlocal seen
            if path.resolve() == source.resolve():
                seen += 1
                if drift and seen > 1:
                    return ordinary
                return expected if fake_matching_input else ordinary
            return original_sha(path)

        def synthetic_generator(_cmd, stage, _logs, env=None) -> None:
            if stage == "extract_elf":
                (work / "original.elf").write_bytes(b"synthetic extracted")
            elif stage == "function_scan":
                (work / "scan/functions.tsv").write_text(
                    "address\tsize\tinstructions\tundecodable\n"
                    "0x1\t2\t1\t0\n")
            elif stage == "generate_functions":
                (work / "generated/recomp.c").write_text(
                    "static const int synthetic = 1;\n")

        reg = {"functions_scanned": 1, "aot_functions_registered": 1,
               "functions_not_in_aot_table": 0}
        report = {"callback_total": 0, "strict_native_runtime_ready": True}
        with (patch.object(prep, "upstream", return_value=root),
              patch.object(prep.preflight, "check", return_value={}),
              patch.object(prep, "sha", side_effect=controlled_sha),
              patch.object(prep, "run", side_effect=synthetic_generator),
              patch.object(prep.coverage, "inspect_file", return_value=reg),
              patch.object(prep.auditor, "sources",
                           side_effect=lambda folder: [folder / "recomp.c"]),
              patch.object(prep.auditor, "audit", return_value=report)):
            if drift:
                try:
                    prep.prepare(root, source, work)
                except ValueError as error:
                    assert "changed during AOT preparation" in str(error)
                else:
                    raise AssertionError("mutated source was trusted")
                assert not (work / "full-original-preparation.json").exists()
                return
            actual = prep.prepare(root, source, work)
        import json
        manifest = json.loads((work / "full-original-preparation.json").read_text())
        assert actual["version_109_verified"] is fake_matching_input
        assert manifest["version_109_verified"] is fake_matching_input
        assert manifest["input_sha256"] == (expected if fake_matching_input else ordinary)
        assert manifest["native_game_boot_proven"] is False
        assert actual["game_boot_proven"] is False
        assert not (work / "original.elf").exists()


if __name__ == "__main__":
    exercise(False)
    exercise(True)
    exercise(True, drift=True)
    print("SHYT_NATIVE_V335_EXACT_109_OWNER_INPUT_ATTESTATION_SYNTHETIC_PASS")
