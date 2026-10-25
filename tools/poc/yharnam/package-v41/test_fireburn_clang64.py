"""Regression for pinned FireBurn FSR host clang64 formatting fix."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shyt_fsr_win_clang64", HERE / "patch_fireburn_clang64.py")
patch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = patch
spec.loader.exec_module(patch)

# Pinned AMD portion from FireBurn/FSR-Vulkan c64f0934.
SOURCE = """// This file is part of the FidelityFX SDK.
#ifdef _WIN32
#include <windows.h>  // required for OutputDebugString()
#endif
void ffxPrintMessage(uint32_t type, const wchar_t* message) {
    wchar_t buffer[512];
    if (type == FFX_MESSAGE_TYPE_ERROR) {
        swprintf_s(buffer, 512, L"FSR_API_DEBUG_ERROR: %ls\\n", message);
    }
    else if (type == FFX_MESSAGE_TYPE_WARNING) {
        swprintf_s(buffer, 512, L"FSR_API_DEBUG_WARNING: %ls\\n", message);
    }
    OutputDebugStringW(buffer);
}
"""

class NativeFsrClang64Tests(unittest.TestCase):
    def test_exact_two_bounded_windows_log_formats(self):
        compiled = patch.transform(SOURCE)
        self.assertIn("#include <cwchar>", compiled)
        self.assertEqual(compiled.count("std::swprintf(buffer, 512,"), 2)
        self.assertEqual(compiled.count("swprintf_s("), 0)
        self.assertIn('std::swprintf(buffer, 512, L"FSR_API_DEBUG_ERROR: %ls\\n", message);', compiled)
        self.assertIn('std::swprintf(buffer, 512, L"FSR_API_DEBUG_WARNING: %ls\\n", message);', compiled)
        self.assertIn("wchar_t buffer[512];", compiled)
        self.assertIn("OutputDebugStringW(buffer);", compiled)

    def test_fail_closed_on_unexpected_vendor_edits_or_second_patch(self):
        with self.assertRaisesRegex(ValueError, "already patched"):
            patch.transform(patch.transform(SOURCE))
        for broken in (
            SOURCE.replace("swprintf_s(buffer, 512", "swprintf_s(buffer, 256", 1),
            SOURCE.replace("wchar_t buffer[512]", "wchar_t buffer[256]"),
            SOURCE.replace("OutputDebugStringW(buffer);", "OutputDebugStringW(other);"),
            SOURCE + 'swprintf_s(buffer, 512, L"additional", message);',
        ):
            with self.subTest(broken=broken[:40]), self.assertRaisesRegex(ValueError, "drifted|additional"):
                patch.transform(broken)

    def test_opticalflow_fixed_arrays_and_no_vendor_drift(self):
        optical = (
            "// This file is part of the FidelityFX SDK.\n"
            + patch.FRAME_HEADER
            + "struct Binding { int index; };\n"
            + "static const Binding srvBindingNames[]={{1},{2}};\n"
            + "static const Binding uavBindingNames[]={{3},{4}};\n"
            + "static const Binding cbBindingNames[]={{5},{6}};\n"
            + "int measure() { return "
            + " + ".join(f"_countof({name})" for name in
                ("srvBindingNames", "uavBindingNames", "cbBindingNames")
                for _ in range(3))
            + "; }\n"
        )
        self.assertEqual(optical.count("_countof("),9)
        patched=patch.transform_opticalflow(optical)
        self.assertEqual(patched.count("std::size("),9)
        self.assertNotIn("_countof(",patched)
        self.assertIn("#include <iterator>",patched)
        with self.assertRaisesRegex(ValueError,"already patched"):
            patch.transform_opticalflow(patched)
        with self.assertRaisesRegex(ValueError,"drifted"):
            patch.transform_opticalflow(optical.replace("_countof(", "_countof (",1))
        with self.assertRaisesRegex(ValueError,"drifted"):
            patch.transform_opticalflow(optical.replace("static const Binding cbBindingNames[]",
                                                         "Binding* cbBindingNames"))
        with self.assertRaisesRegex(ValueError,"drifted"):
            patch.transform_opticalflow(optical.replace(patch.FRAME_HEADER,"#include <algorithm>\n"))

    def test_frame_interpolation_fixed_arrays_and_strict_source_provenance(self):
        # Exact ABI-safe replacement for 14 fixed-array MSVC _countof uses.
        # This synthetic source deliberately mirrors all known call sites.
        original = (
            "// This file is part of the FidelityFX SDK.\\n"
            + patch.FRAME_HEADER
            + "int test() { int array[4] = {1,2,3,4};\\n"
            + "int values[] = {1,2};\\n"
            + "".join(f"int n{i} = _countof(array);\\n" for i in range(12))
            + "int selected[_countof(values)] = {};\\n"
            + "return _countof(selected); }\\n"
        )
        self.assertEqual(original.count("_countof("), patch.FRAME_COUNT)
        patched = patch.transform_frame_interpolation(original)
        self.assertIn("#include <iterator>", patched)
        self.assertEqual(patched.count("std::size("), patch.FRAME_COUNT)
        self.assertEqual(patched.count("_countof("), 0)
        with self.assertRaisesRegex(ValueError, "already patched"):
            patch.transform_frame_interpolation(patched)
        with self.assertRaisesRegex(ValueError, "drifted"):
            patch.transform_frame_interpolation(original.replace("_countof(", "_countof (", 1))
        with self.assertRaisesRegex(ValueError, "drifted"):
            patch.transform_frame_interpolation(original.replace(patch.FRAME_HEADER, "#include <algorithm>\\n"))

if __name__ == "__main__":
    unittest.main()
