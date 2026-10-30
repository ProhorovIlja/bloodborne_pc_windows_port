"""V140 regression: only upstream YT #451, exactly one Ludwig wall."""
from pathlib import Path
import importlib.util
import unittest

p = Path(__file__).with_name("stage_ludwig_multiplayer_wall_v140.py")
spec = importlib.util.spec_from_file_location("ludwig_wall_v140", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture(function: str) -> str:
    return "prefix\n" + function + "\nbool IsParamOfType(std::span<const u8> param, std::string_view type) { suffix"

def test_fixture() -> str:
    return (m.TEST_START +
            "    const auto walls = MultiplayerWalls();\n" +
            m.TEST_OLD + "\n" +
            "    const auto on = [&](u32 map) { return 0; };\n" +
            m.TEST_MAP_ANCHOR + "\n" +
            "}\n\n// Player report 2026-10-22: the Forbidden Woods' wall")

class NativeLudwigWallV140Tests(unittest.TestCase):
    def test_exact_upstream_function_adds_ludwig_once(self):
        old = fixture(m.EXPECTED_OLD_FUNCTION)
        reviewed = fixture(m.EXPECTED_NEW_FUNCTION)
        changed = m.replace_function(old, reviewed)
        self.assertEqual(changed, reviewed)
        self.assertEqual(changed.count("3401801"), 1)
        self.assertIn("std::array<s32, 19>", changed)
        self.assertIn("m34_00 event 13400010", changed)
        self.assertIn("object + 2000", changed)
        self.assertEqual(changed[:len("prefix\n")], "prefix\n")
        cpp = m.native_test_fragment(changed)
        self.assertIn("int main()", cpp)
        self.assertIn("objects.count(3401801)", cpp)
    def test_original_cpp_and_reviewed_method_drift_fail_closed(self):
        base = fixture(m.EXPECTED_OLD_FUNCTION)
        upstream = fixture(m.EXPECTED_NEW_FUNCTION)
        for changed in (base.replace("3201999", "3201998"),
                        base.replace("std::array<s32, 18>", "std::array<s32, 20>"),
                        upstream):
            with self.subTest(changed=changed[:30]):
                with self.assertRaises(ValueError): m.replace_function(changed, upstream)
        with self.assertRaises(ValueError):
            m.replace_function(base, upstream.replace("3401801", "3401802"))
        with self.assertRaises(ValueError):
            m.native_test_fragment(base)
    def test_exact_original_upstream_regression_only(self):
        base = test_fixture()
        reviewed = base.replace(m.TEST_OLD, m.TEST_NEW).replace(
            m.TEST_MAP_ANCHOR, m.TEST_MAP_NEW)
        self.assertEqual(m.replace_test(base, reviewed), reviewed)
        self.assertIn("on(0x22000000)", reviewed)
        for bad in (reviewed.replace("m34_00", "m34_01"),
                    reviewed + "unreviewed change",
                    reviewed.replace("19u", "20u")):
            with self.subTest(bad=bad[-35:]):
                with self.assertRaises(ValueError): m.replace_test(base, bad)
    def test_pinned_blobs_are_explicit_and_source_only(self):
        self.assertEqual(m.BASE_PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.REVIEWED_PIN, "3b0a0d8dc86d9ae726e2b0e836a46b4f46a346ed")
        self.assertEqual(m.BASE_BLOBS[m.GAME], "5186b4ed9fa9387752f4dc21362950d70d062505")
        self.assertEqual(m.REVIEWED_BLOBS[m.GAME], "3c54d313ea0312b647d6ae503abf306de4aba7b8")
        self.assertEqual(m.normalized(b"a\r\nb\r\n"), b"a\nb\n")
        self.assertNotEqual(m.blob_sha(b"wrong"), m.BASE_BLOBS[m.GAME])

if __name__ == "__main__":
    unittest.main()
