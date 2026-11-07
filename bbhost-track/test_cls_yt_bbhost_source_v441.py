#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Local synthetic regression for V441: no proprietary game files."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from verify_cls_yt_bbhost_source_v441 import Refused, verify

HOST = ("""
#include "bbcoop.h"
void yt_host_install() { bbcoop_install(nullptr, 0, nullptr, 0, nullptr); }
void yt_host_register() { bbnet_register(); }
void bbhost_yt_game_menu() {}
""" + "// source fixture line\n" * 25)

class V441Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic-source.zip"

    def make_zip(self, *, missing=False, game=False, duplicate=False, host=HOST):
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("source/src/yt/yt_host.cpp", host)
            z.writestr("source/src/yt/yt_ui.cpp", "void bbhost_yt_game_menu() {}\n")
            if not missing:
                z.writestr("source/src/yt/yt_host.h", "#pragma once\n")
            if game:
                z.writestr("source/assets/eboot.bin", b"NEVER_INCLUDE_GAME_CONTENT")
            if duplicate:
                z.writestr("other/src/yt/yt_host.cpp", HOST)
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_valid_real_loader_shape(self):
        digest = self.make_zip()
        r = verify(self.path, digest)
        self.assertEqual(r["source_files_checked"], 3)
        self.assertTrue(all(r["required"].values()))
        self.assertEqual(r["proof_only"], "source-provenance-and-hook-loader-not-playability")

    def test_wrong_archive_sha_refused(self):
        self.make_zip()
        with self.assertRaises(Refused):
            verify(self.path, "0" * 64)

    def test_missing_yt_source_refused(self):
        digest = self.make_zip(missing=True)
        with self.assertRaises(Refused):
            verify(self.path, digest)

    def test_no_integrated_game_loader_refused(self):
        digest = self.make_zip(host="void unrelated() {}\n" * 25)
        with self.assertRaises(Refused):
            verify(self.path, digest)

    def test_proprietary_game_file_refused(self):
        digest = self.make_zip(game=True)
        with self.assertRaises(Refused):
            verify(self.path, digest)

    def test_ambiguous_loader_refused(self):
        digest = self.make_zip(duplicate=True)
        with self.assertRaises(Refused):
            verify(self.path, digest)

    def test_zip_slip_refused(self):
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("../escapes.txt", "unsafe")
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(Refused):
            verify(self.path, digest)

if __name__ == "__main__":
    unittest.main(verbosity=2)
