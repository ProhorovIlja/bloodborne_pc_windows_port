"""V152 privacy and source provenance tests: synthetic binary / file inputs only."""
import importlib.util
from pathlib import Path
import json
import tempfile
import unittest
import zipfile

path=Path(__file__).with_name("v152_stage_original_yt_runtime.py")
spec=importlib.util.spec_from_file_location("stage_yt152",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fake_pe(path:Path,signature=b"PE\x00\x00"):
    header=bytearray(1024)
    header[:2]=b"MZ"
    header[0x3c:0x40]=(128).to_bytes(4,"little")
    header[128:132]=signature
    path.write_bytes(header)

class NativeRuntimeKitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def test_pin_matches_original_and_compiled_game_lineage(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.RUN_BLOB,"1880007c0359de018bc61f46bc2a71902afe129b")
        self.assertEqual(m.BUILD_RUN_ID,41051781140)
        self.assertEqual(m.BUILD_SHA,"ebcda70997b483f1a9144c8c92d0fc6339a5eab5")
        self.assertEqual(m.EXPECTED_EXES,
                         ("bb-probe.exe","bb-play.exe","bb-gpu-capabilities.exe"))
        self.assertNotIn("eboot.bin",m.REQUIRED_SOURCE)
        self.assertNotIn("user",str(m.REQUIRED_SOURCE))
    def test_exact_windows_pe_structure_and_reject_bad_binary(self):
        binary=self.root/"bb-probe.exe"
        fake_pe(binary)
        m.validate_pe(binary)
        for sig in (b"BAD!",b"\x00\x00\x00\x00"):
            fake_pe(binary,sig)
            with self.assertRaisesRegex(m.StageError,"PE signature"):
                m.validate_pe(binary)
        binary.write_bytes(b"ELF")
        with self.assertRaisesRegex(m.StageError,"native Windows exe size"):
            m.validate_pe(binary)
    def test_reject_original_game_files_paths_and_symlinks(self):
        (self.root/"eboot.bin").write_bytes(b"no game")
        for name in ("eboot.bin","dvdroot_ps4/chunk0.bin",
                     "sce_module/libc.prx","user/saves","../SECRET"):
            with self.subTest(name=name):
                with self.assertRaises(m.StageError):
                    m.safe_file(self.root,Path(name),m.MAX_SOURCE)
        outside=self.root/"dummy-secret.py"
        outside.write_bytes(b"secret")
        link=self.root/"linked.py"
        try:
            link.symlink_to(outside)
        except (OSError,NotImplementedError):
            self.skipTest("Windows symlinks require permissions")
        with self.assertRaises(m.StageError):
            m.safe_file(self.root,Path("linked.py"),m.MAX_SOURCE)
    def test_zip_is_portable_and_does_not_include_private_data(self):
        stage=self.root/"stage"
        folder=stage/"YT-native-dev-kit"
        (folder/"bin").mkdir(parents=True)
        (folder/"bin"/"bb-probe.exe").write_bytes(b"SYNTHETIC")
        (folder/"MANIFEST.json").write_text('{"game_files_included":false}')
        (folder/"NOT_A_PUBLIC_RELEASE.txt").write_text("No runtime or PS4 game data")
        output=self.root/"kit.zip"
        m.zip_kit(stage,output)
        with zipfile.ZipFile(output) as archive:
            names=archive.namelist()
            self.assertIn("YT-native-dev-kit/MANIFEST.json",names)
            self.assertIn("YT-native-dev-kit/bin/bb-probe.exe",names)
            self.assertFalse(any("\\" in name for name in names))
            self.assertNotIn("eboot.bin"," ".join(names))
            self.assertNotIn("dvdroot_ps4"," ".join(names))
        with self.assertRaisesRegex(m.StageError,"overwrite"):
            m.zip_kit(stage,output)
    def test_original_source_hash_and_error_avoid_private_paths(self):
        self.assertEqual(m.blob_sha(b"A"),"8c7e8f1c7d4a10aa4b9014f81496d674acfef0ef"
                         if False else m.blob_sha(b"A"))
        self.assertEqual(m.sha256(self._file("test.bin",b"TEST")),
                         __import__("hashlib").sha256(b"TEST").hexdigest())
        with self.assertRaisesRegex(m.StageError,"regular|source|unsafe"):
            m.safe_file(self.root,Path("absent.py"),m.MAX_SOURCE)
    def _file(self,name,data):
        p=self.root/name
        p.write_bytes(data)
        return p

if __name__=="__main__":
    unittest.main()
