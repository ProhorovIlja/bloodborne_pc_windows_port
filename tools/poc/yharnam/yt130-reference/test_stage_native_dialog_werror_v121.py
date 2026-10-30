"""V121 source-pin and compile ABI sanity for genuine YT1.3 Win64 C failure."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

p=Path(__file__).with_name("stage_native_dialog_werror_v121.py")
spec=importlib.util.spec_from_file_location("yt121_dialog_clang_fix",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NativeWindowsCommonDialog(unittest.TestCase):
    def source(self):
        return ("#include <stdint.h>\n#define ABI\n" + m.BEFORE + "\n" +
                "struct Export {const char *name; int32_t (*callback)(void);};\n" +
                "struct Export exports[] = {" + m.REGISTRATION + "};\n")

    def test_only_dead_global_removed_exported_function_and_result_stay(self):
        old=self.source()
        new=m.rewrite(old)
        self.assertIn(m.MARK,new)
        self.assertNotIn("common_initialized=1;",new)
        self.assertIn("static ABI int32_t common_init(void) { return 0; }",new)
        self.assertIn(m.REGISTRATION,new)
        self.assertEqual(new.replace(m.AFTER,m.BEFORE),old)
        self.assertEqual(m.BLOB,"2e62aadf665b5c19d3fabe4536f31da9a060536f")
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")

    def test_source_drift_double_application_and_missing_abi_refuse(self):
        original=self.source()
        with self.assertRaisesRegex(ValueError,"source drift"):
            m.rewrite(m.rewrite(original))
        for old in (m.BEFORE,m.REGISTRATION):
            with self.subTest(old=old[:35]):
                with self.assertRaises(ValueError):
                    m.rewrite(original.replace(old,"BROKEN",1))

    def test_native_clang_strict_werror_and_real_c_abi(self):
        clang=shutil.which("clang")
        if clang is None:
            self.skipTest("clang unavailable in this host; Win CLANG64 CI required")
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/"test_original_common_dialog_export.c"
            src.write_text(m.rewrite(self.source()) +
                           "\nint main(void) {return exports[0].callback();}\n",
                           encoding="utf-8")
            p=subprocess.run([clang,"-std=c11","-Wall","-Wextra","-Werror",
                              "-Wunused-but-set-global","-fsyntax-only",str(src)],
                             capture_output=True,text=True,timeout=12)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)

if __name__=="__main__":
    unittest.main()
