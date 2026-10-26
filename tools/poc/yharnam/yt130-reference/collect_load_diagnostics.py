#!/usr/bin/env python3
"""Only snapshot synthetic upstream loadtest log lines from a disposed local server.

Upstream run_load.py --keep sends 'server folder: /tmp/shadnet-load-*'
to stderr. Never copy any link_key.bin, SQLite, config, saves or secrets.
Only text shadnet.log and bbloadN.log; tail limited and sanitized for
accidental IPs and authenticated token/password literals.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re

FOLDER = re.compile(r"(?m)^server folder:\s+(/tmp/shadnet-load-[A-Za-z0-9_-]+)\s*$")
SENSITIVE = re.compile(r"(?i)(password|authorization|bearer|secret|private.key|api.token)(\s*[:=]\s*)(\S+)")
MAX_SOURCE = 2 * 1024 * 1024

def collect(stderr: Path) -> str:
    if not stderr.is_file() or stderr.is_symlink():
        raise ValueError("Missing synthetic load stderr")
    raw = stderr.read_text(encoding="utf-8", errors="replace")
    found = FOLDER.findall(raw)
    if len(found) != 1:
        raise ValueError("Expected one isolated upstream temp server folder")
    folder = Path(found[0])
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Missing private local synthetic folder")
    msgs = []
    for file in sorted([folder / "shadnet.log", *folder.glob("bbload[0-9]*.log")]):
        if not file.is_file() or file.is_symlink() or file.stat().st_size > MAX_SOURCE:
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()[-120:]
        safe = SENSITIVE.sub(r"\1\2[REDACTED]", "\n".join(lines))
        msgs.append(f"== {file.name} ==\n{safe[:32000]}")
    if not msgs:
        raise ValueError("Synthetic shadnet and bbload logs not found")
    return "\n".join(msgs) + "\n"

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run_stderr",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    msg=collect(args.run_stderr)
    args.output.write_text(msg,encoding="utf-8")
    print("SHYT_SYNTHETIC_LOG_DIAGNOSIS")
    print(msg[-12000:])
