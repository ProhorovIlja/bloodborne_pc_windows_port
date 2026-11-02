#!/usr/bin/env python3
"""Synthetic offline release-integrity tests. No commercial game or binaries."""
from __future__ import annotations
import hashlib
from pathlib import Path
import tempfile
import unittest
from verify_yt_v131_release import OFFICIAL,check

class ReleaseIntegrityTests(unittest.TestCase):
    def test_pinned_released_baseline(self):
        self.assertEqual(sorted(OFFICIAL),[
            "YharnamTogether-v1.3.1-portable.zip",
            "YharnamTogether-v1.3.1-setup.exe"])
        self.assertEqual(OFFICIAL["YharnamTogether-v1.3.1-setup.exe"][0],127500183)
        self.assertEqual(OFFICIAL["YharnamTogether-v1.3.1-portable.zip"][0],198394703)
        self.assertEqual(OFFICIAL["YharnamTogether-v1.3.1-setup.exe"][1],
            "21f9fb0fbb1d48b96ed614dc9cfbc7bc88e55c407015db82a30da72cc317e76a")
        self.assertEqual(OFFICIAL["YharnamTogether-v1.3.1-portable.zip"][1],
            "f87883bdcb729325fdbcc6d8292f56304eed60c4039cd34192141c9ba4a13db1")

    def test_exact_name_size_digest_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"local.zip"
            content=b"fully invented testing bytes"
            p.write_bytes(content)
            marker={p.name:(len(content),hashlib.sha256(content).hexdigest())}
            self.assertTrue(check(p,marker))
            self.assertFalse(check(p)) # public CLI cannot accept synthetic manifest
            p.write_bytes(b"other invented test payload")
            self.assertFalse(check(p,marker))
            p.write_bytes(content)
            self.assertFalse(check(p,{p.name:(len(content)+1,marker[p.name][1])}))
            self.assertFalse(check(p,{p.name:(len(content),"00"*32)}))
            self.assertFalse(check(p,{"another-file.zip":marker[p.name]}))
            q=Path(d)/"alias.zip"
            q.symlink_to(p)
            self.assertFalse(check(q,{q.name:marker[p.name]}))

    def test_missing_file_fails_closed(self):
        self.assertFalse(check(Path("/no-yharnam-131-asset-here.exe")))
if __name__=="__main__":
    unittest.main()
