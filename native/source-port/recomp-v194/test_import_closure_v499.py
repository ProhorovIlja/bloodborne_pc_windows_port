# SPDX-License-Identifier: GPL-2.0-or-later
import unittest

from import_closure_v499 import compare


class TestImportClosure(unittest.TestCase):
    digest = "a" * 64
    fn = ["ABCDEFGHIJK", "lib", "mod", 2]
    obj = ["ABCDEFGHIJK", "lib", "mod", 1]
    imports = {8: (7, 0, (b"ABCDEFGHIJK", b"lib", b"mod", 2)),
               16: (6, 0, (b"ABCDEFGHIJK", b"lib", b"mod", 2)),
               24: (6, 0, (b"ABCDEFGHIJK", b"lib", b"mod", 1))}

    def profile(self, *rows):
        return dict(format="bb-host-import-inventory-v1", image_sha256=self.digest,
                    bindings=list(rows))

    def test_exact_scope_and_symbol_type(self):
        report = compare(self.imports, self.profile(self.fn, ["ABCDEFGHIJK", "lib", "other", 1]), self.digest)
        self.assertEqual((report["required_keys"], report["required_slots"]), (2, 3))
        self.assertEqual((report["matched_keys"], report["matched_slots"]), (1, 2))
        self.assertEqual(report["missing_keys"], [self.obj])
        self.assertEqual(report["unused_profile_keys"], 1)

    def test_metadata_complete_is_not_runtime_verified(self):
        report = compare(self.imports, self.profile(self.fn, self.obj), self.digest)
        self.assertEqual(report["missing_keys"], [])
        self.assertFalse(report["runtime_bindings_verified"])

    def test_refuse_invalid_profiles(self):
        for rows, digest in [((self.fn,), "b"*64), ((self.fn, self.fn), self.digest),
                             ((["ABCDEFGHIJK", "lib", "mod", True],), self.digest),
                             ((["ABCDEFGHIJK", "lib#", "mod", 2],), self.digest)]:
            with self.subTest(rows=rows, digest=digest), self.assertRaises(ValueError):
                compare(self.imports, self.profile(*rows), digest)

    def test_empty_requirements_refused(self):
        with self.assertRaises(ValueError):
            compare({}, self.profile(), self.digest)
