#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V232 tests pinned official YT 1.3.1 mods.py without actual game files."""
import json
import pathlib
import sys
import tempfile

from yt_launcher_mod_conflicts_v232 import canonical, inspect, load_upstream


def put(root: pathlib.Path, path: str, contents=b"synthetic"):
    target = root.joinpath(*path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contents)


def run(upstream_mods_py: pathlib.Path):
    upstream = load_upstream(upstream_mods_py)
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        mods = root / "mods"
        mods.mkdir()
        put(mods / "A Cosmetic", "dvdroot_ps4/parts/Hunter.dcx")
        put(mods / "B Cosmetic", "dvdroot_ps4/parts/hunter.DCX")
        put(mods / "C Gameplay", "dvdroot_ps4/param/GameParam.parambnd.dcx")
        put(mods / "D Gameplay", "DVDROOT_PS4/PARAM/gameparam.PARAMBND.DCX")
        put(mods / "E Alone", "dvdroot_ps4/sound/new_sound.bnd")
        put(mods / "Disabled", "dvdroot_ps4/event/e123.emevd.dcx")
        base = root / "CUSA03173-mods"
        put(base, "dvdroot_ps4/parts/hunter.dcx")
        profile = root / "mods.json"
        profile.write_text(json.dumps({
            "order": ["D Gameplay", "C Gameplay", "A Cosmetic",
                      "B Cosmetic", "E Alone", "Disabled"],
            "disabled": ["Disabled"]
        }))
        report = inspect(upstream, mods, profile, base, fingerprint_gameplay=True)
        assert len(report["effective_gameplay_override_fingerprint_sha256"]) == 64
        assert report["enabled_mod_count"] == 5, report
        assert report["enumerated_game_files"] == 6, report
        assert report["file_replacements_between_mod_layers"] == 3, report
        assert report["distinct_game_targets"] == 3, report
        assert report["mod_precedence"] == [
            "CUSA03173-mods [base overlay]", "D Gameplay", "C Gameplay",
            "A Cosmetic", "B Cosmetic", "E Alone"], report
        assert report["reported_gameplay_critical_conflicts"] == 1, report
        collisions = {c["game_path"]: c for c in report["reported_conflicts"]}
        assert collisions["dvdroot_ps4/param/gameparam.parambnd.dcx"]["winner"] == "C Gameplay"
        assert collisions["dvdroot_ps4/parts/hunter.dcx"]["winner"] == "B Cosmetic"
        assert "Disabled" not in report["mod_precedence"]
        assert not report["mod_binary_compatibility_proven"]
        assert not report["original_game_modified"]
        assert "Doll" not in json.dumps(report)
        # The checksum is over final gameplay winners, not folder names.
        digest_before = report["effective_gameplay_override_fingerprint_sha256"]
        same = inspect(upstream, mods, profile, base, fingerprint_gameplay=True)
        assert same["effective_gameplay_override_fingerprint_sha256"] == digest_before
        put(mods / "C Gameplay", "dvdroot_ps4/param/GameParam.parambnd.dcx", b"modified")
        changed = inspect(upstream, mods, profile, base, fingerprint_gameplay=True)
        assert changed["effective_gameplay_override_fingerprint_sha256"] != digest_before
        # Cosmetic-only replacements must not change the gameplay checksum.
        stable = changed["effective_gameplay_override_fingerprint_sha256"]
        put(mods / "B Cosmetic", "dvdroot_ps4/parts/hunter.DCX", b"new-cosmetic")
        assert inspect(upstream, mods, profile, base,
                       fingerprint_gameplay=True)[
                           "effective_gameplay_override_fingerprint_sha256"] == stable

        # Malformed/unsafe layouts must stop preflight, not silently apply.
        # Windows filesystems usually collapse upper/lower-case paths.
        # Inject a duplicated *enumeration* of the real public loader's
        # existing source instead of depending on filesystem case support.
        actual_mod_files = upstream.mod_files
        def case_duplicate(folder):
            rows = list(actual_mod_files(folder))
            for row in rows:
                yield row
            if folder.name == "E Alone":
                assert len(rows) == 1
                yield (pathlib.Path("DVDROOT_PS4/SOUND/NEW_SOUND.BND"), rows[0][1])
        upstream.mod_files = case_duplicate
        try:
            try:
                inspect(upstream, mods, profile, base)
            except ValueError as exc:
                assert "duplicate target" in str(exc), str(exc)
            else:
                raise AssertionError("casefold collision within same mod passed")
        finally:
            upstream.mod_files = actual_mod_files

        # Disabling the cosmetic mod should remove its layer.
        profile.write_text(json.dumps({"order": ["A Cosmetic"], "disabled": [
            "B Cosmetic", "D Gameplay", "C Gameplay", "Disabled"]}))
        selected_report = inspect(upstream, mods, profile)
        assert selected_report["file_replacements_between_mod_layers"] == 0
        assert selected_report["enabled_mod_count"] == 2  # A + E
        assert selected_report["mod_precedence"] == ["A Cosmetic", "E Alone"]

        assert canonical(pathlib.Path("dvdroot_ps4/Param/abc.dcx")) == (
            "dvdroot_ps4/param/abc.dcx", True)
        for filename in ["dvdroot_ps4/sce_module/hack.bin",
                         "dvdroot_ps4/chr/../../../evil.bin",
                         "other/chr/abc.dcx", "dvdroot_ps4/chr/X:y.dcx"]:
            try:
                canonical(pathlib.Path(filename))
            except ValueError:
                pass
            else:
                raise AssertionError(f"accepted unsafe file name {filename}")
    print("SHYT_V232_REAL_YT131_MOD_LOADER_CONFLICT_PREFLIGHT_PASS")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_v232.py path/to/original/real/mods.py")
    run(pathlib.Path(sys.argv[1]))
