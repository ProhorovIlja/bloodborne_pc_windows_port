"""V100: original Sirit std::abort compile failure and source-drift tests."""
import importlib.util
import unittest
from pathlib import Path

source = Path(__file__).with_name("patch_sirit_abort_v100.py")
spec = importlib.util.spec_from_file_location("shyt_sirit_v100",source)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PIN = """#pragma once
#include <bit>
#include <span>
#include <cassert>
#include <concepts>
#include <cstddef>
#include <functional>
namespace Sirit {
void AbortNow() {
            std::abort();
}
}
"""
class SiritAbortV100Tests(unittest.TestCase):
    def test_standard_cstdlib_header_before_std_abort(self):
        fixed=mod.patch_header(PIN)
        self.assertIn(mod.MARKER,fixed)
        self.assertLess(fixed.index("#include <cstdlib>"),fixed.index("std::abort();"))
        self.assertEqual(fixed.count("#include <cstdlib>"),1)
        with self.assertRaisesRegex(ValueError,"already includes"):
            mod.patch_header(fixed)

    def test_unknown_header_is_not_modified(self):
        for old in (
            PIN.replace("#include <cstddef>","#include <stddef.h>"),
            PIN.replace("std::abort()","abort()"),
            PIN.replace("namespace Sirit {","namespace unrelated {"),
            PIN+PIN,
        ):
            with self.subTest(old=old[:70]),self.assertRaisesRegex(ValueError,"drift|unknown"):
                mod.patch_header(old)

if __name__ == "__main__":
    unittest.main()
