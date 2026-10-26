"""V111 bounded Clang64 Ninja concurrency is exact and opt-in over a known pin."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "shyt_v111_ninja_guard", Path(__file__).with_name("patch_native_ninja_jobs_v111.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FIXTURE = """case $(uname -s) in
MINGW*|MSYS*)
    # SHYT-V103-NATIVE-BBNET-FIRST
    if ! ninja -C out/gpu bbnet > out/bbnet-build.log 2>&1; then
        exit 1
    fi
    # SHYT-V106-BBNET-ONLY
    if [[ ${SHYT_BBNET_ONLY:-0} == 1 ]]; then
        exit 0
    fi
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then
        exit 1
    fi
    ;;
esac
"""


class V111BoundedRealGameNinja(unittest.TestCase):
    def test_both_actual_targets_limited_without_modifying_target_list(self):
        result = mod.transform(FIXTURE)
        self.assertEqual(result.count('ninja -j "${SHYT_NATIVE_NINJA_JOBS:-2}"'), 2)
        self.assertIn(' -C out/gpu bbnet > out/bbnet-build.log 2>&1', result)
        self.assertIn(' -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1', result)
        self.assertLess(result.index("bbnet >"), result.index("bb-probe bb-gpu-capabilities"))
        self.assertIn("SHYT-V106-BBNET-ONLY", result)
        self.assertIn("SHYT-V111-NINJA-BOUNDED-COMPILE", result)

    def test_reapplication_and_source_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, "already applied"):
            mod.transform(mod.transform(FIXTURE))
        for bad in (
            FIXTURE.replace("SHYT-V106-BBNET-ONLY", "removed"),
            FIXTURE.replace("ninja -C out/gpu bbnet", "not-a-native-target"),
            FIXTURE.replace("bb-probe", "unknown-target"),
            FIXTURE + FIXTURE,
        ):
            with self.subTest(bad=bad[:80]), self.assertRaises(ValueError):
                mod.transform(bad)


if __name__ == "__main__":
    unittest.main()
