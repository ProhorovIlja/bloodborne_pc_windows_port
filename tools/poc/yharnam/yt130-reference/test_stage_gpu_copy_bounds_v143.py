"""V143 GPU CopyBuffer source-exact C++ boundary regression."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("stage_gpu_copy_bounds_v143.py")
spec=importlib.util.spec_from_file_location("original_gpu_copy_bounds_v143",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class OriginalCopyBoundsV143Tests(unittest.TestCase):
    @staticmethod
    def original():
        return (m.HEADER_OLD + "other\n" + m.METHOD_OLD +
                "    const bool bounded = copies.size() > 4;\n"
                "    for (const auto& copy : copies) {\n"
                "        src_max = std::max<u64>(src_max, copy.srcOffset + copy.size);\n"
                "        dst_max = std::max<u64>(dst_max, copy.dstOffset + copy.size);\n"
                "    }\n"
                "    scheduler.Record([regions = scheduler.RecordData(copies)](auto command){ });\n")
    def test_original_copy_optimized_barrier_and_vulkan_paths_preserved(self):
        new=m.rewrite(self.original())
        self.assertIn("if (copies.empty()) {\n        return;",new)
        self.assertIn("copy.size <= src_size - copy.srcOffset",new)
        self.assertIn("copy.size <= dst_size - copy.dstOffset",new)
        self.assertIn("copies = filtered;",new)
        self.assertIn("const bool bounded = copies.size() > 4;",new)
        self.assertLess(new.index("copies = filtered;"),new.index("const bool bounded"))
        self.assertLess(new.index("const bool bounded"),new.index("scheduler.RecordData(copies)"))
        self.assertIn("std::atomic<u32> warned",new)
        self.assertIn("warned.fetch_add(1, std::memory_order_relaxed) < 16",new)
        self.assertEqual(new.count("const bool bounded = copies.size() > 4;"),1)
        self.assertEqual(new.count("#include <vector>"),1)
    def test_invalid_copy_treated_as_no_submission_before_vulkan(self):
        def safe(src,dst,src_offset,dst_offset,size):
            return (src_offset<=src and size<=src-src_offset and
                    dst_offset<=dst and size<=dst-dst_offset)
        cases=[
            (100,200,0,0,100,True), (100,200,100,200,0,True),
            (100,200,100,0,1,False), (100,200,0,201,0,False),
            (100,200,5,20,80,True),
            (100,200,(1<<64)-1,0,(1<<64)-1,False),
        ]
        for src,dst,src_of,dst_of,n,expected in cases:
            with self.subTest(copy=(src_of,dst_of,n)):
                self.assertEqual(safe(src,dst,src_of,dst_of,n),expected)
    def test_missing_repeated_or_modified_original_fails_closed(self):
        original=self.original()
        for old in (m.METHOD_OLD,m.HEADER_OLD):
            with self.subTest(old=old[:35]):
                with self.assertRaisesRegex(ValueError,"source drift"):
                    m.rewrite(original.replace(old,"broken",1))
        with self.assertRaisesRegex(ValueError,"source drift"):
            m.rewrite(m.rewrite(original))
        with self.assertRaisesRegex(ValueError,"not exact pinned"):
            m.transform(original.encode())
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOB,"4d7505de7c0381d48f2d4c98351d2ba3262b1183")
        self.assertEqual(m.normalized(b"x\r\ny\r\n"),b"x\ny\n")
    def test_unreviewed_recorder_removed_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"barrier/record"):
            m.rewrite(self.original().replace("regions = scheduler.RecordData(copies)","regions = bad(copies)"))

if __name__=="__main__":
    unittest.main()
