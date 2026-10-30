#!/usr/bin/env python3
"""V130 wrapper: preserve only new non-PII Qt send statistics with existing wire QA.

Original measure_wire_traffic.py already handles bounded original bbload,
temporary localhost shadnet, process cleanup, 32/64/100/200 game load,
reliable CoopStream and Qt eventloop logs. It removes isolated temp folder
after reading. Read *only* the new aggregate SEND_PROBE lines first, then
allow original implementation to parse and delete that temp folder.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import re
import measure_wire_traffic as wire

LOG=re.compile(
    r"YT130_SEND_PROBE calls=(\d+) hub=(\d+) world=(\d+) errors=(\d+)"
    r" busy_us=(\d+) max_call_us=(\d+) max_pending_bytes=(\d+)"
)
FIELDS=("calls","hub","world","errors","busy_us","max_call_us","max_pending_bytes")
original_extract=wire.extract_server_counters


def parse_send(lines: list[str]) -> dict:
    total={field:0 for field in FIELDS}
    windows=0
    for line in lines:
        if m:=LOG.search(line):
            windows+=1
            for name,number in zip(FIELDS,m.groups()):
                n=int(number)
                total[name]=max(total[name],n) if name in ("max_call_us","max_pending_bytes") else total[name]+n
    return {"windows":windows,"metrics":total}


def extract_with_send_probe(stderr: str, output: Path) -> tuple:
    folders=wire.FOLDER.findall(stderr)
    if len(folders)==1:
        folder=Path(folders[0])
        if (not folder.is_symlink() and folder.is_dir()
                and folder.parent==Path("/tmp")):
            path=folder/"shadnet.log"
            if path.is_file() and not path.is_symlink():
                matched=[line for line in path.read_text(encoding="utf-8",errors="replace").splitlines()
                         if "YT130_SEND_PROBE calls=" in line]
                target=output.with_name(output.stem.replace("wire-","send-")+".json")
                target.write_text(json.dumps(parse_send(matched),indent=2)+"\n",encoding="utf-8")
    return original_extract(stderr,output)


if __name__=="__main__":
    wire.extract_server_counters=extract_with_send_probe
    p=argparse.ArgumentParser()
    p.add_argument("--shadnet",type=Path,required=True)
    p.add_argument("--bbload",type=Path,required=True)
    p.add_argument("--load-script",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    raise SystemExit(wire.run(args))
