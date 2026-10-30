"""DLC missing prepareFlip upstream source/behavior checks without game assets."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location(
    "yt130_v131",Path(__file__).with_name("stage_dlc_flip_guard_v131.py"))
assert spec and spec.loader
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.before='\n'.join([s[0] for s in guard.INCLUDES])+'\n'+guard.ORIGINAL_CALL
        self.reviewed='\n'.join([
            guard.BLOCK_START+" (from upstream)","    if (!BbFlipMarker::HasPrepareFlip(cmdbuf, size_dw)) {",
            "VideoOut::sceVideoOutSubmitFlip(", "return result != ORBIS_OK ? result : flip_result;",
            "    }\n",guard.ORIGINAL_CALL
        ])
        self.header="inline bool HasPrepareFlip( const int* dcb ) {return dcb!=nullptr;}"
        self.test="int main(){ FindPrepareFlip(nullptr, 300, 256); }"
    def test_upstream_safe_fallback_and_original_patch_call_retained(self):
        fixed=guard.change(self.before,guard.CMAKE_BEFORE,self.reviewed,self.header,self.test)
        src=fixed[guard.DRIVER]
        self.assertIn("BbFlipMarker::HasPrepareFlip",src)
        self.assertIn("VideoOut::sceVideoOutSubmitFlip(",src)
        self.assertIn(guard.ORIGINAL_CALL,src)
        self.assertLess(src.index("BbFlipMarker::HasPrepareFlip"),src.index(guard.ORIGINAL_CALL))
        self.assertIn("#include <atomic>",src)
        self.assertIn("flip-marker-test",fixed[guard.CMAKE])
        self.assertEqual(fixed[guard.HEADER],self.header)
        self.assertEqual(fixed[guard.TEST],self.test)
    def test_double_stage_and_missing_source_guard_refused(self):
        patched=guard.change(self.before,guard.CMAKE_BEFORE,self.reviewed,self.header,self.test)
        with self.assertRaises(ValueError):
            guard.change(patched[guard.DRIVER],guard.CMAKE_BEFORE,self.reviewed,self.header,self.test)
        with self.assertRaises(ValueError):
            guard.change(self.before.replace("gnmdriver.h","not-original.h"),
                         guard.CMAKE_BEFORE,self.reviewed,self.header,self.test)
        with self.assertRaises(ValueError):
            guard.change(self.before,guard.CMAKE_BEFORE,"bad",self.header,self.test)
        with self.assertRaises(ValueError):
            guard.change(self.before,guard.CMAKE_BEFORE,self.reviewed,self.header,"no null test")
    def test_source_locked_to_yt13_original_and_upstream(self):
        self.assertEqual(guard.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(guard.UPSTREAM,"8d106f40c90ef681adbe025c47cc75d289e0ef7b")
        for path in (guard.DRIVER,guard.HEADER,guard.CMAKE):
            self.assertTrue(path.startswith("bbport/gpu/"))

if __name__=="__main__":
    unittest.main()
