"""Source integration tests for the complete upstream Vulkan texture GC port.

The numeric policy unit tests alone miss missing renderer API declarations,
which caused the real Windows engine build to fail. This detects the same
partial integration before invoking the long Windows C++ link.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GcIntegrationTests(unittest.TestCase):
    def test_complete_renderer_and_statistics_contract(self):
        texture = (ROOT / "gpu/shadps4/video_core/texture_cache/texture_cache.cpp").read_text()
        header = (ROOT / "gpu/shadps4/video_core/renderer_vulkan/vk_instance.h").read_text()
        implementation = (ROOT / "gpu/shadps4/video_core/renderer_vulkan/vk_instance.cpp").read_text()
        stats = (ROOT / "gpu/shim/bbport_toggles.h").read_text()
        assert "gc_policy.h" in (ROOT / "gpu/shadps4/video_core/texture_cache/texture_cache.h").read_text()
        self.assertIn("GetDeviceBlockSlack() const;", header)
        self.assertIn("u64 Instance::GetDeviceBlockSlack() const {", implementation)
        self.assertIn("vmaGetHeapBudgets(allocator, budgets.data())", implementation)
        self.assertIn("stats.blockBytes - stats.allocationBytes", implementation)
        self.assertIn("instance.GetDeviceBlockSlack()", texture)
        self.assertIn("GcPolicy::EffectiveUsage", texture)
        self.assertIn("gc_quota.Begin", texture)
        for name in ("gc_freed_bytes_total", "gc_write_backs_total",
                     "gc_ns_total", "gc_level"):
            self.assertRegex(stats, rf"\b{re.escape(name)}\b\s*(?:\{{0\}}|,)")
            self.assertIn("BbStats::" + name, texture)

    def test_uses_same_policy_in_test_and_renderer(self):
        policy = ROOT / "gpu/shadps4/video_core/texture_cache/gc_policy.h"
        unit = ROOT / "tests/test_gc_policy.cpp"
        cmake = (ROOT / "gpu/CMakeLists.txt").read_text()
        self.assertTrue(policy.is_file())
        self.assertTrue(unit.is_file())
        self.assertIn("GcPolicy::MarksFor", (ROOT / "gpu/shadps4/video_core/texture_cache/texture_cache.cpp").read_text())
        self.assertIn("gc-policy-test", cmake)


if __name__ == "__main__":
    unittest.main()
