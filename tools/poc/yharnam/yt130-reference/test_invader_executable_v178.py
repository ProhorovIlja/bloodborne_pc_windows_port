#!/usr/bin/env python3
"""Regression for V177 native executable naming on POSIX and Windows/MinGW."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from check_native_invader_actual_session_v177 import resolve_output_binary


class NativeInvaderOutputTests(unittest.TestCase):
    def test_posix_output_without_suffix(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "native-invader"
            target.touch()
            self.assertEqual(resolve_output_binary(target), target.resolve())

    def test_mingw_output_appends_exe(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "native-invader"
            exe = Path(str(target) + ".exe")
            exe.touch()
            self.assertEqual(resolve_output_binary(target), exe.resolve())

    def test_missing_output_fails_closed(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                resolve_output_binary(Path(directory) / "missing")

    def test_ambiguous_outputs_fail_closed(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "native-invader"
            exe = Path(str(target) + ".exe")
            target.touch()
            exe.touch()
            with self.assertRaises(FileNotFoundError):
                resolve_output_binary(target)


if __name__ == "__main__":
    unittest.main()
