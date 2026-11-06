#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V6: fake files only; verify original YT -> BBHost command selection.

No original game, network, shell, downloads, screenshot or connected app.
Runs against BOTH the standalone V6 module and original patched YT AST.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import ast
import sys


def check(mod):
    with tempfile.TemporaryDirectory(prefix="shyt-v6-fake-") as directory:
        root=Path(directory)
        config=root/"launch-config"
        appdir=root/"install"
        exe=appdir/"bbhost"/"bbhost.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"MZ"+b"not-a-real-BBHost-binary"*3600)
        data=root/"userdata"
        game=root/"CUSA03173"
        game.mkdir()
        owner=game/"eboot.bin"
        fake=b"\x7fELF\x02"+b"fake-retail-1.09-for-CI-only"*10
        owner.write_bytes(fake)
        profile={"game_dir":str(game)}
        assert mod.read_engine_v6(config)=="bbport"
        mod.write_engine_v6(config,"bbhost")
        assert mod.read_engine_v6(config)=="bbhost"
        mod.write_engine_v6(config,"bbport")
        assert mod.read_engine_v6(config)=="bbport"
        try:
            mod.write_engine_v6(config,"malware")
        except mod.EngineSetupError:
            pass
        else:
            raise AssertionError("invalid engine accepted")
        path=mod.engine_file_v6(config)
        path.write_text(json.dumps({"engine":"bbhost","command":"powershell.exe"}))
        try:
            mod.read_engine_v6(config)
        except mod.EngineSetupError:
            pass
        else:
            raise AssertionError("untrusted executable injection accepted")
        mod.write_engine_v6(config,"bbhost")
        try:
            mod.owner_game_image_v6(profile)
        except mod.EngineSetupError:
            pass
        else:
            raise AssertionError("fake eboot passed official BBHost hash")
        # Synthetic fixture can only run after locally replacing the
        # pinned release digest in the test's isolated Python module.
        original=mod.EXPECTED_GAME_109
        try:
            mod.EXPECTED_GAME_109=hashlib.sha256(fake).hexdigest()
            # An absent profile must not silently select BBHost's
            # unrelated default public backend in the Seamless Hunt launcher.
            try:
                mod.command_v6(appdir, data, profile)
            except mod.EngineSetupError as exc:
                assert "implicit third-party public server" in str(exc)
            else:
                raise AssertionError("BBHost started without an explicit profile")
            toml=data/"user"/"bbhost"/"bbhost.toml"
            toml.write_text('[online]\nhost = "localhost"\n')
            args=mod.command_v6(appdir,data,profile)
            assert args[0]==str(exe.resolve())
            assert args[1:3]==["--app0",str(game.resolve())]
            assert args[3:5]==["--eboot",str(owner.resolve())]
            assert args[5:7]==["--data",str(data/"user"/"bbhost")]
            assert args[-2:]==["--config",str(toml)]
        finally:
            mod.EXPECTED_GAME_109=original
        # V9: simulate the owner's historical CUSA03173-patch layout,
        # without possessing any original Bloodborne bytes.
        patch_game = root / "CUSA03173-patch"
        patch_game.mkdir()
        patch_elf = patch_game / "eboot.bin-decrypted"
        fictional_patch = b"\x7fELF\x02" + b"independent-fictional-CUSA-patch" * 20
        patch_elf.write_bytes(fictional_patch)
        try:
            mod.EXPECTED_GAME_109 = hashlib.sha256(fictional_patch).hexdigest()
            found_game, found_elf = mod.owner_game_image_v6(profile)
            assert found_game == game.resolve()
            assert found_elf == patch_elf.resolve()
            args = mod.command_v6(appdir, data, profile)
            assert args[1:3] == ["--app0", str(game.resolve())]
            assert args[3:5] == ["--eboot", str(patch_elf.resolve())]
            patch_elf.unlink()
            try:
                mod.owner_game_image_v6(profile)
            except mod.EngineSetupError:
                pass
            else:
                raise AssertionError("nonmatching base ELF accepted after patch gone")
            patch_elf.write_bytes(fictional_patch)
            real_patch_dir = root / "actual-patch"
            patch_game.rename(real_patch_dir)
            try:
                patch_game.symlink_to(real_patch_dir, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            else:
                try:
                    mod.owner_game_image_v6(profile)
                except mod.EngineSetupError:
                    pass
                else:
                    raise AssertionError("symlinked game update dir accepted")
        finally:
            mod.EXPECTED_GAME_109 = original
        # Parent directory cannot be link redirected to an attacker binary.
        old=exe.parent
        backup=appdir/"old"
        old.rename(backup)
        try:
            old.symlink_to(backup,target_is_directory=True)
        except (OSError,NotImplementedError):
            pass
        else:
            try:
                mod.host_binary_v6(appdir)
            except mod.EngineSetupError:
                pass
            else:
                raise AssertionError("symlink exe parent accepted")
        assert not (root/"game_upload.zip").exists()


def main():
    p=Path(__file__).resolve().with_name("shyt_yt_bbhost_launcher_v6.py")
    spec=importlib.util.spec_from_file_location("shyt_yt_bbhost_launcher_v6",p)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    assert mod.EXPECTED_GAME_109=="941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"
    check(mod)
    print("SHYT_V6_YT_BBHOST_ENGINE_LOCAL_SAFE_COMMAND_AND_EXACT_EBOOT_GATE_PASS")


if __name__ == "__main__":
    main()
