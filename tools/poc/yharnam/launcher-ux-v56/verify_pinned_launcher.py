#!/usr/bin/env python3
"""Check V46+V56+V57 composition against the full pinned Yharnam Together BLauncher.

Use alongside a sparse GitHub checkout of lKaniel/bloodborne-server at the
exact SHA pinned by the source-of-truth contract. No game executable needed.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(original: Path) -> None:
    if not original.is_file():
        raise FileNotFoundError("real pinned BLauncher source missing: " + str(original))
    raw = original.read_text(encoding="utf-8")
    if ("COOP_TEST = True" not in raw or
            "Yharnam Together: Bloodborne Seamless Co-op" not in raw or
            "def build_coop_popup(self):" not in raw):
        raise ValueError("unexpected Yharnam Together source at pinned path")
    v46 = load("shyt_v46_remote_ports", ROOT / "tools/poc/yharnam/remote-profile-v46/patch_remote_ports.py")
    v56 = load("shyt_v56_ui", ROOT / "tools/poc/yharnam/launcher-ux-v56/patch_onboarding.py")
    with_remote = v46.transform_launcher(raw)
    v57 = load("shyt_v57_tcp_probe", ROOT / "tools/poc/yharnam/launcher-ux-v56/patch_connection_probe.py")
    polished = v57.transform(v56.transform(with_remote))
    compile(polished, str(original), "exec")
    if (polished.count("SHYT-V46-REMOTE-LAUNCHER-PORTS") != 1 or
            polished.count("SHYT_LAUNCHER_ONBOARDING_V56") != 1 or
            polished.count("SHYT_LAUNCHER_TCP_DIAG_V57") != 1):
        raise AssertionError("V46 remote profile or V56 UI missing after source composition")
    for essential in ("self.coop_import_saves", "self.coop_search(None)",
                      "self.coop_changed", "self.coop_ready()",
                      "self.build_coop_custom", "self.coop_probe_server",
                      "shyt_tcp_backend_probe", "COOP_TEST = True"):
        if essential not in polished:
            raise AssertionError("required original launcher behavior lost: " + essential)
    if polished.count("bbport_coop.save_settings") != raw.count("bbport_coop.save_settings"):
        raise AssertionError("unexpected change to co-op account / save persistence")
    print("SHYT_V57_FULL_PINNED_BLAUNCHER_V46_V56_COMPOSITION_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pinned_launcher", type=Path)
    args = parser.parse_args()
    run(args.pinned_launcher)


if __name__ == "__main__":
    main()
