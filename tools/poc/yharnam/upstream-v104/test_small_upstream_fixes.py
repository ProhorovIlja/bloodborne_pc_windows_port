import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("patch_small_upstream_fixes.py")
spec = importlib.util.spec_from_file_location("v104_upstream", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PARTY = """std::vector<MultiplayerWall> MultiplayerWalls() {
    // InitializeEvent(_, 7600, object, sfx) in m22-m35's event files (01.09).
    static constexpr std::array<s32, 18> Walls{
        2201999, 2301999, 2401999, 2401998, 2401997, 2401996, 2401995, 2411999, 2411998,
        2411997, 2421999, 2421998, 2701999, 2701998, 2801999, 2801998, 3201999, 3501990,
    };
    for (const s32 object : Walls) {
        walls.push_back(MultiplayerWall{object, object + 2000});
    }
}"""
LAUNCHER = """def run_role(argv):
    attach_stdio()
    for stream in (sys.stdout, sys.stderr):  # keep messages in order with the game's output
        try:
            stream.reconfigure(line_buffering=True)
        except (AttributeError, ValueError):
            pass
    if argv[0] == '--script':
        pass"""

class UpstreamV104(unittest.TestCase):
    def test_ludwig_wall_and_original_registry_intact(self):
        result = module.patch_party(PARTY)
        self.assertIn("std::array<s32, 19> Walls", result)
        self.assertIn("3401801,", result)
        self.assertIn("2201999", result)
        self.assertIn("3501990", result)
        self.assertIn("object + 2000", result)
        self.assertEqual(result.count("3401801"), 1)
        self.assertIn("event 13400010", result)
    def test_launcher_utf8_and_preserved_error_semantics(self):
        result = module.patch_launcher(LAUNCHER)
        self.assertIn("encoding='utf-8', errors='replace', line_buffering=True", result)
        self.assertIn("except (AttributeError, ValueError)", result)
        self.assertIn("if argv[0] == '--script':", result)
    def test_composition_exact_inputs(self):
        result = module.patch({module.PARTY: PARTY, module.LAUNCHER: LAUNCHER})
        self.assertEqual(set(result), set(module.FILES))
        with self.assertRaisesRegex(ValueError, "exact"):
            module.patch({module.PARTY: PARTY})
    def test_repeated_application_fails_closed(self):
        for fn, text in [(module.patch_party, PARTY), (module.patch_launcher, LAUNCHER)]:
            with self.assertRaisesRegex(ValueError, "drift"):
                fn(fn(text))
    def test_source_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Ludwig"):
            module.patch_party(PARTY.replace("3501990", "3501991"))
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            module.patch_launcher(LAUNCHER.replace("line_buffering=True", "line_buffering=False"))

if __name__ == "__main__":
    unittest.main()
