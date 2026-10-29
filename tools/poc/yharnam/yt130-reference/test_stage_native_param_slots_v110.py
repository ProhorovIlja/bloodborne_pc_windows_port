"""Source locked v1.3 original client upstream PR442 PARAM slot-cache gate."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("stage_native_param_slots_v110.py")
spec=importlib.util.spec_from_file_location("yt130_slots_v110",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

SPAN="SHYT-YT130-PR442-PARAM-SPAN-V109"

def sources():
    return {
        m.CPP: "// "+SPAN+"\n"+"u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size) {",
        m.HEADER: "// "+SPAN+"\n"+"u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size);",
        m.RULES: "// "+SPAN+"\n"+m.OLD_RULE_FUNCTION,
        m.TEST: "// "+SPAN+"\nTEST(LoadedParamMemory, Existing) {}\n",
    }

class NativeParamSlotTests(unittest.TestCase):
    def test_native_client_caches_only_last_validated_slot(self):
        original=sources()
        patched=m.patch(original)
        self.assertEqual(set(patched),set(m.FILES))
        self.assertIn("LoadedParamSlots::Found",patched[m.CPP])
        self.assertIn("class LoadedParamSlots",patched[m.HEADER])
        self.assertIn("std::scoped_lock guard{cache_mutex}",patched[m.RULES])
        self.assertIn("remembered = slots.Slot(type)",patched[m.RULES])
        self.assertIn("slots.Found(type, slot)",patched[m.RULES])
        self.assertIn("HasMemoryAccess(param, 0x40",patched[m.RULES])
        self.assertEqual(patched[m.RULES].count("const u64 repository = "),1)
        self.assertNotIn("for (u64 slot = 0; slot < 0x2000; slot += 8) {\n        const u64 holder",patched[m.RULES])
        self.assertIn("TEST(LoadedParamSlots, RememberEachTypeAndUpdateAfterReload)",patched[m.TEST])
        self.assertEqual(patched[m.TEST][:len(original[m.TEST])],original[m.TEST])

    def test_pin_drift_reapply_and_out_of_order_rejected(self):
        original=sources()
        with self.assertRaisesRegex(ValueError,"reapplication"):m.patch(m.patch(original))
        for key in m.FILES:
            bad=dict(original)
            bad[key]="invalid original source"
            with self.subTest(key=key):
                with self.assertRaises(ValueError):m.patch(bad)
        with self.assertRaisesRegex(ValueError,"all four"):m.patch({m.CPP:original[m.CPP]})
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")

if __name__=="__main__":
    unittest.main()
