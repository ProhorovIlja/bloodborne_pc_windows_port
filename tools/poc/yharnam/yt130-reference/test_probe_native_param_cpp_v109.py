"""Original YT1.3 staged native PARAM helper extraction safety tests."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("probe_native_param_cpp_v109.py")
s=importlib.util.spec_from_file_location("param_cpp_probe",p)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class ParamCppProbeTests(unittest.TestCase):
    def test_exact_actual_compiled_function_slice_only(self):
        source="// " + m.TAG + "\n" + m.CPP_HEAD + "\n" + (
            "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size) {\n"
            "    const u64 entries = 0x40 + u64{rows} * 24;\n"
            "    if (param.size() < entries) return std::numeric_limits<u64>::max();\n"
            "    u64 offset = 0;\n"
            "    std::memcpy(&offset, param.data(), sizeof(offset));\n"
            "    return offset + row_size;\n"
            "}\n\nRecreatePlan PlanRecreate(x);")
        result=m.extract(source)
        self.assertTrue(result.startswith("u64 ParamTableSize("))
        self.assertTrue(result.endswith("}\n"))
        self.assertNotIn("RecreatePlan",result)

    def test_unknown_client_drift_cannot_be_compiled_as_original(self):
        for bad in ("", "u64 ParamTableSize() {}", "// "+m.TAG, m.CPP_HEAD):
            with self.subTest(bad=bad[:35]):
                with self.assertRaises(ValueError):m.extract(bad)

if __name__=="__main__":
    unittest.main()
