#!/usr/bin/env python3
"""Fail-closed local smoke of the real Yharnam Together Python backend.

Executes the actual pinned backend with the selected Python interpreter, not
a mocked server. Probes its status, regional server-info and login endpoints.
Captures up to 8KiB of process stderr if it crashes. No live ports, accounts,
secrets, retail game assets, or production server dependencies.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import http.client
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


class BackendSmokeFailure(RuntimeError):
    pass


def free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def exercise(backend: Path, python: Path | str = sys.executable,
             *, timeout: float = 12) -> list[tuple[str, str, int]]:
    if not backend.is_file():
        raise BackendSmokeFailure(f"pinned Python backend script missing: {backend}")
    if timeout <= 0 or timeout > 60:
        raise ValueError("smoke timeout must be between 0 and 60 seconds")
    port = free_port()
    command = [str(python), "-u", str(backend.resolve()),
               "--address", "127.0.0.1", "--port", str(port)]
    with tempfile.TemporaryDirectory(prefix="shyt-backend-preflight-") as temp:
        stderr_path = Path(temp) / "backend-output.log"
        with stderr_path.open("wb") as writer:
            proc = subprocess.Popen(command, stdout=writer, stderr=subprocess.STDOUT,
                                    cwd=temp)
            results: list[tuple[str, str, int]] = []
            try:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        raise BackendSmokeFailure(
                            f"reference backend exited early: exit {proc.returncode}")
                    try:
                        with closing(http.client.HTTPConnection(
                                "127.0.0.1", port, timeout=1.0)) as client:
                            client.request("GET", "/status")
                            response = client.getresponse()
                            data = response.read()
                            if response.status != 200:
                                raise BackendSmokeFailure(
                                    f"status response code is {response.status}, not 200")
                            results.append(("GET", "/status", response.status))
                        break
                    except (ConnectionRefusedError, TimeoutError, ConnectionResetError,
                            http.client.RemoteDisconnected, BrokenPipeError):
                        time.sleep(0.12)
                else:
                    raise BackendSmokeFailure("reference backend did not answer /status")
                for method, path, body in [
                    ("GET", "/bb-eu/ss.info", None),
                    ("POST", "/login", b'{"MessageId":"LoginRequest","SessionId":"s","PlatformAccountId":"test-only"}')
                ]:
                    with closing(http.client.HTTPConnection(
                            "127.0.0.1", port, timeout=2.0)) as client:
                        headers = {"Content-Type": "application/json"} if body else {}
                        client.request(method, path, body=body, headers=headers)
                        response = client.getresponse()
                        payload = response.read()
                        if response.status != 200 or not payload:
                            raise BackendSmokeFailure(
                                f"unexpected {method} {path}: status {response.status}, "
                                f"bytes {len(payload)}")
                        results.append((method, path, response.status))
                return results
            except (OSError, http.client.HTTPException) as exc:
                raise BackendSmokeFailure(
                    f"reference backend connection failed: {type(exc).__name__}: {exc}") from exc
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=4)
                writer.flush()
                if len(results) < 3:
                    print("SHYT_REFERENCE_BACKEND_DIAGNOSTICS_BEGIN", file=sys.stderr)
                    with stderr_path.open("rb") as f:
                        print(f.read()[-8192:].decode("utf-8", "replace"), file=sys.stderr)
                    print("SHYT_REFERENCE_BACKEND_DIAGNOSTICS_END", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", type=Path, required=True)
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()
    try:
        results = exercise(args.backend, args.python)
    except (BackendSmokeFailure, OSError, ValueError) as exc:
        print("YT_PYTHON_BACKEND_SMOKE_FAILED:", exc, file=sys.stderr)
        return 1
    for method, path, status in results:
        print(f"PASS {method} {path}: {status}")
    print("YT_PYTHON_BACKEND_SMOKE_PASS: pinned backend speaks expected routes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
