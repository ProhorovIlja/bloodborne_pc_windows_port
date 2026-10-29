"""Pin-sensitive AMD FSR CLANG64 compatibility regression tests."""
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "shyt_pinned_fsr_wprintf", HERE/"patch_pinned_fsr_windows_wprintf.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

FSR = '''// Copyright (C) 2025 Advanced Micro Devices, Inc.
#include <FidelityFX/host/ffx_message.h>
#include <FidelityFX/host/ffx_util.h>
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
'''


class FsrCompatibilityTest(unittest.TestCase):
    def test_exact_two_bounded_rewrites_without_unrelated_changes(self):
        patched = mod.patch_text(FSR)
        self.assertEqual(patched.count("std::swprintf(buffer, 512,"), 2)
        self.assertEqual(patched.count("#include <cwchar>"), 1)
        self.assertNotIn("swprintf_s(", patched)
        self.assertIn("OutputDebugStringW(buffer)", patched)
        self.assertIn("AMD", patched)
        self.assertIn("wchar_t buffer[512]", patched)
        self.assertEqual(
            patched.replace(
                "#include <cwchar>  // std::swprintf is portable to MinGW CLANG64\n",
                "").replace("std::swprintf(", "swprintf_s("),
            FSR,
        )

    def test_source_drift_and_double_application_fail_closed(self):
        for bad in [
            FSR.replace("swprintf_s(", "swprintf(", 1),
            FSR.replace("wchar_t buffer[512];", "wchar_t buffer[1024];"),
            FSR.replace("OutputDebugStringW(buffer)", "puts(\"a\")"),
            FSR.replace("Copyright (C) 2025 Advanced Micro Devices, Inc.",
                        "unknown vendor"),
        ]:
            with self.subTest(bad=bad[:80]):
                with self.assertRaises(ValueError):
                    mod.patch_text(bad)
        with self.assertRaisesRegex(ValueError, "already applied"):
            mod.patch_text(mod.patch_text(FSR))

    def test_on_disk_requires_real_upstream_blob(self):
        with TemporaryDirectory() as d:
            file = Path(d)/"ffx_message.cpp"
            file.write_text(FSR, encoding="utf-8")
            before = file.read_bytes()
            with self.assertRaisesRegex(ValueError, "version mismatch"):
                mod.patch_file(file)
            self.assertEqual(file.read_bytes(), before)
        self.assertEqual(mod.git_blob(b"test"),
                         "30d74d258442c7c65512eafab474568dd706c430")


if __name__ == "__main__":
    unittest.main()
