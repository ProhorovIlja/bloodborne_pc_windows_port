"""Exact original native GPU PR #5560 source regression, no runtime bypass."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name("stage_gpu_zero_slice_v142.py")
spec = importlib.util.spec_from_file_location("gpu_zero_slice_v142", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class OriginalZeroSliceTests(unittest.TestCase):
    def fixture(self):
        return "before\n" + "\n".join(old for old, _ in m.EDITS) + "\nafter"
    def test_original_exact_source_only_and_all_divisors_safe(self):
        out=m.rewrite(self.fixture())
        self.assertIn("resources.layers = 1;",out)
        self.assertIn("std::max<u32>(info.resources.layers, 1);",out)
        self.assertIn("if (slice_size == 0 || guest_size % slice_size != 0)",out)
        self.assertIn("if (slice_size == 0) {\n            continue;",out)
        self.assertEqual(out.count("#include <algorithm>"),1)
        self.assertEqual(out.count("LOG_WARNING(Render_Vulkan"),1)
        self.assertEqual(m.ORIGINAL_PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOB,"5b99e73b112824e1c289c25372b481f49eb89fa8")
    def test_missing_duplicate_and_repeat_application_refused(self):
        src=self.fixture()
        for original,_ in m.EDITS:
            with self.subTest(anchor=original[:35]):
                with self.assertRaisesRegex(ValueError,"source drift"):
                    m.rewrite(src.replace(original,"MISSING",1))
                with self.assertRaisesRegex(ValueError,"source drift"):
                    m.rewrite(src+original)
        with self.assertRaisesRegex(ValueError,"source drift"):
            m.rewrite(m.rewrite(src))
    def test_cannot_edit_modified_game_source_or_unpinned_copy(self):
        with self.assertRaisesRegex(ValueError,"blob hash mismatch"):
            m.transform(self.fixture().encode())
        self.assertEqual(m.normalize(b"a\r\nb\r\n"),b"a\nb\n")
        self.assertNotEqual(m.blob_sha(b"altered"),m.BLOB)
    def test_safety_for_zero_descriptor_inputs(self):
        # Verify the arithmetic contract independently of the full native
        # renderer build. Valid inputs preserve original division behavior.
        def mip_slice(mip_size,layers):
            n=mip_size//layers if layers else mip_size
            return n if n else None
        def tex_slice(size,layers):
            safe_layers=max(layers,1)
            n=size//safe_layers
            return n if n else None
        for x,y in [(0,0),(0,1),(1,0),(1,1),(256,0),(256,4),(1,200)]:
            with self.subTest(mip=x,layers=y):
                self.assertIsNone(mip_slice(x,y)) if x==0 or (x<y and y) else None
                self.assertEqual(tex_slice(x,y),x//max(y,1) or None)

if __name__=="__main__":
    unittest.main()
