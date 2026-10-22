"""Pure display labels for the Seamless Hunt launcher's compact Home screen.

Labels are deliberately *not* claims of full game compatibility, live account
sign-in, or legacy CLS BBSC cross-play. Pre-launch validation remains separate.
"""
from pathlib import Path


def game_label(selected: str, path_valid: bool) -> str:
    if not selected:
        return "Choose your own Bloodborne game folder to begin"
    if not path_valid:
        return "Game location missing or invalid · choose another folder"
    label = Path(selected).name if not str(selected).lower().endswith("eboot.bin") else Path(selected).parent.name
    return f"{label} selected · exact build checked before Play"


def client_label(executable_present: bool, runner_present: bool) -> str:
    if not executable_present:
        return "Native client missing · Windows engine must be built/installed"
    if not runner_present:
        return "Launch script missing · repair client installation"
    return "Native client files found · gameplay not yet verified"


def party_label(mode: str) -> str:
    if mode == "host":
        return "Native party: Hosting · not CLS BBSC bell compatibility"
    if mode == "join":
        return "Native party: Joining · not CLS BBSC bell compatibility"
    return "Solo · native party disabled · legacy BBSC not enabled"
