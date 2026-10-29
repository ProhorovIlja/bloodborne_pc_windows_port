"""Pinned YT1.3 source-guard tests of upstream PR442 guest PARAM stutter fix."""
import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).with_name("stage_native_param_memory_v109.py")
SPEC = importlib.util.spec_from_file_location("yt130_param_v109", FILE)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def fixture():
    return {
        m.CPP: "// real native party logic\nRecreatePlan PlanRecreate(std::span<const std::optional<std::string>> found,\n",
        m.HEADER: "bool IsParamOfType(std::span<const u8> param, std::string_view type);\n",
        m.RULES: ("    u64 size = entries;\n"
                  "    for (u64 row = 0; row < rows; ++row) {\n"
                  "        size = std::max(size, ReadValue<u64>(param, 0x40 + row * 24 + 8) + row_size);\n"
                  "    }\n"),
        m.TEST: "// original real gtest end\n",
    }


class NativeParamMemoryStageTest(unittest.TestCase):
    def test_ports_original_cxx_game_logic_and_real_gtests(self):
        output = m.patch(fixture())
        self.assertEqual(set(output), set(m.FILES))
        self.assertIn("std::memcpy(&offset, param.data()", output[m.CPP])
        self.assertIn("std::numeric_limits<u64>::max()", output[m.CPP])
        self.assertIn("param.size() < entries", output[m.CPP])
        self.assertIn("u64 ParamTableSize(", output[m.HEADER])
        self.assertIn("const u64 size = ParamTableSize(", output[m.RULES])
        self.assertNotIn("ReadValue<u64>(param, 0x40 + row * 24 + 8)", output[m.RULES])
        self.assertIn("TEST(LoadedParamMemory, FullTableSpanFindsFurthestOffset", output[m.TEST])
        self.assertIn("TEST(LoadedParamMemory, RejectsTruncatedAndOverflowingEntries)", output[m.TEST])
        self.assertEqual(output[m.TEST].count("TEST(LoadedParamMemory"), 2)

    def test_source_drift_double_stage_and_partial_inputs_fail_closed(self):
        original = fixture()
        with self.assertRaisesRegex(ValueError, "already applied"):
            m.patch(m.patch(original))
        with self.assertRaisesRegex(ValueError, "exact four"):
            m.patch({m.CPP: original[m.CPP]})
        for key in m.FILES[:3]:
            bad = dict(original)
            bad[key] = "some other official file\n"
            with self.subTest(file=key):
                with self.assertRaisesRegex(ValueError, "source anchor drift"):
                    m.patch(bad)
        # The original +4 pattern is a precise single anchor, never a global
        # sed replacement that risks modifying unrelated enemy scaling.
        bad = dict(original)
        bad[m.RULES] += bad[m.RULES]
        with self.assertRaisesRegex(ValueError, "source anchor drift"):
            m.patch(bad)

    def test_only_expected_original_file_set_and_unmodified_test_prefix(self):
        original = fixture()
        modified = m.patch(original)
        self.assertEqual(modified[m.TEST][:len(original[m.TEST])], original[m.TEST])
        self.assertEqual(len(m.FILES), 4)
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertIn("21k", m.PARAM_FUNCTION)


if __name__ == "__main__":
    unittest.main()
