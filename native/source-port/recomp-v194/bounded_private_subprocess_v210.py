#!/usr/bin/env python3
"""V210 fail-bounded private subprocess runner for whole-original-game stages.

This is NOT a fix for ChatGPT infrastructure stream failures. It removes
unbounded capture_output from the original ELF scanner/recompiler pipeline,
drains continuously, retains only the head/tail in a private 0600 log,
kills timed-out stages, and never prints game bytes/addresses/paths.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
from threading import Thread
from typing import Sequence

HEAD = 32768
TAIL = 32768
BLOCK = 4096
MAX_STEP = 48


def run_stage(argv: Sequence[object], step: str, log_dir: Path, *,
              env: dict[str, str] | None = None, timeout: float = 7200) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", step):
        raise ValueError("unsafe stage identifier")
    if not 0 < timeout <= 7200:
        raise ValueError("stage timeout must be within two hours")
    dest = log_dir.absolute()
    if dest.is_symlink() or any((p / ".git").exists() for p in (dest, *dest.parents)):
        raise ValueError("private log directory must remain outside Git")
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not dest.is_dir() or dest.is_symlink():
        raise ValueError("unsafe private log directory")
    logfile = dest / (step + ".log")
    summary = dest / (step + ".summary.json")
    if logfile.exists() or summary.exists():
        raise ValueError("this private stage already ran; use a fresh work directory")
    if not argv:
        raise ValueError("empty stage command")

    head = bytearray()
    tail = bytearray()
    total = 0
    reader_error: list[str] = []
    proc = subprocess.Popen([str(a) for a in argv], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=env, start_new_session=(os.name == "posix"))
    assert proc.stdout is not None

    def drain() -> None:
        nonlocal total
        try:
            while True:
                chunk = proc.stdout.read(BLOCK)
                if not chunk:
                    break
                total += len(chunk)
                if len(head) < HEAD:
                    head.extend(chunk[:HEAD - len(head)])
                tail.extend(chunk)
                if len(tail) > TAIL:
                    del tail[:len(tail) - TAIL]
        except OSError:
            reader_error.append("stream_read_failed")
        finally:
            proc.stdout.close()

    thread = Thread(target=drain, daemon=True)
    thread.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.wait()
    thread.join(timeout=10)
    if thread.is_alive():
        reader_error.append("stream_drain_incomplete")

    # Keep only bounded private diagnostics, never the entire command output.
    marker = b"\n[... PRIVATE TOOL OUTPUT TRUNCATED ...]\n"
    kept = bytes(head) if total <= HEAD else (
        bytes(head) + marker + bytes(tail) if total > HEAD + TAIL else bytes(head) +
        bytes(tail)[HEAD - total:]
    )
    fd = os.open(logfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(kept)
    result = {
        "status": "timeout" if timed_out else (
            "failed" if proc.returncode != 0 or reader_error else "passed"),
        "step": step,
        "returncode": proc.returncode,
        "output_bytes_seen": total,
        "output_bytes_kept": len(kept),
        "truncated": total > len(kept),
        "reader_error": bool(reader_error),
    }
    fd = os.open(summary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
        file.write("\n")
    if result["status"] != "passed":
        raise RuntimeError(f"private stage {step} failed; inspect bounded private diagnostic")


def selftest() -> None:
    with tempfile.TemporaryDirectory() as folder:
        dest = Path(folder) / "logs"
        run_stage([sys.executable, "-c", "print('A'*200000)"], "large", dest,
                  timeout=15)
        summary = json.loads((dest / "large.summary.json").read_text())
        assert summary["status"] == "passed"
        assert summary["truncated"]
        assert (dest / "large.log").stat().st_size < HEAD + TAIL + 100
        assert summary["output_bytes_seen"] > 200000
        try:
            run_stage([sys.executable, "-c", "import sys;sys.exit(7)"],
                      "failed", dest, timeout=10)
        except RuntimeError:
            pass
        else:
            raise AssertionError("stage failure lost")
        assert json.loads((dest / "failed.summary.json").read_text())["status"] == "failed"
        try:
            run_stage([sys.executable, "-c", "import time;time.sleep(3)"],
                      "timeout", dest, timeout=0.1)
        except RuntimeError:
            pass
        else:
            raise AssertionError("timeout not enforced")
        assert json.loads((dest / "timeout.summary.json").read_text())["status"] == "timeout"
        assert "200000" not in (dest / "large.summary.json").read_text()
    print("SHYT_NATIVE_V210_BOUNDED_PRIVATE_STREAM_SELFTEST_PASS")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if not args.self_test:
        ap.error("run_stage is called from private V204, only --self-test standalone")
    selftest()
