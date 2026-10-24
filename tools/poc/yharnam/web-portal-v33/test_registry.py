"""Security guard for research-only upstream catalog."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import unittest

class CandidateRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((Path(__file__).parent/"source_registry.json").read_text("utf-8"))
    def test_all_candidates_not_executable_install_actions(self):
        self.assertFalse(self.data["auto_install"])
        self.assertEqual(self.data["schema_version"],1)
        entries=self.data["entries"]
        self.assertGreaterEqual(len(entries),5)
        self.assertEqual(len({e["id"] for e in entries}),len(entries))
        for item in entries:
            with self.subTest(item=item["id"]):
                self.assertEqual(item["review_state"],"research_only")
                self.assertNotIn("public-realm",item["allowed_modes"])
                self.assertIn("license_review",item)
                self.assertGreater(len(item["why"]),25)
    def test_sources_are_web_pages_not_executables(self):
        for item in self.data["entries"]:
            p=urlsplit(item["source"])
            self.assertEqual(p.scheme,"https")
            self.assertIn(p.netloc,{"github.com","www.nexusmods.com"})
            self.assertFalse(p.path.endswith((".exe",".zip",".dll",".pkg")))
            self.assertFalse(p.username or p.password)
if __name__=="__main__":
    unittest.main()
