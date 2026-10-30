"""Source-exact V139 regression tests: shadPS4 #5577 cache IO atomicity."""
import importlib.util
from pathlib import Path
import unittest
p = Path(__file__).with_name("stage_cache_io_atomic_v139.py")
sp = importlib.util.spec_from_file_location("cache_v139", p)
m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)

class CacheAtomicTests(unittest.TestCase):
    def fixture(self):
        return "\n".join([old for old, _ in m.CHANGES] +
            ["++num_requests;", "--num_requests;"])
    def test_atomic_worker_counter_without_changing_io_queue(self):
        s = m.rewrite(self.fixture())
        self.assertIn("#include <atomic>", s)
        self.assertIn("std::atomic<u32> num_requests{};", s)
        self.assertEqual(s.count("num_requests.load(std::memory_order_acquire)"), 2)
        self.assertIn("++num_requests;", s)
        self.assertIn("--num_requests;", s)
    def test_rejects_missing_double_or_repeated_application(self):
        src = self.fixture()
        with self.assertRaises(ValueError): m.rewrite(m.rewrite(src))
        for before, _ in m.CHANGES:
            with self.subTest(before=before):
                with self.assertRaisesRegex(ValueError, "source drift"):
                    m.rewrite(src.replace(before, "BROKEN", 1))
                with self.assertRaisesRegex(ValueError, "source drift"):
                    m.rewrite(src + "\n" + before)
    def test_windows_crlf_canonicalization_only(self):
        raw = b"first\nsecond\n"
        windows = b"first\r\nsecond\r\n"
        self.assertEqual(m.canonical_source(windows), raw)
        self.assertEqual(m.git_blob_sha(m.canonical_source(windows)),
                         m.git_blob_sha(raw))
        self.assertNotEqual(m.canonical_source(b"first edited\r\n"),
                            raw)
        with self.assertRaisesRegex(ValueError, "not exact pinned"):
            m.transform(windows)

    def test_does_not_accept_unpinned_or_modified_game_source(self):
        with self.assertRaisesRegex(ValueError, "not exact pinned"):
            m.transform(self.fixture().encode())
        self.assertEqual(m.UPSTREAM_PIN,
                         "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOB_PIN,
                         "65a7df5eb8aff2bdb128467c4680182ca2ef8080")

if __name__ == "__main__":
    unittest.main()
