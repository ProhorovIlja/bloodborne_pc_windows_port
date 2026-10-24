#!/usr/bin/env python3
"""Pin-checked, CI-only diagnostics for the Python backend parity reference.

This does not modify gameplay or shadNet semantics and cannot turn a
failing parity comparison into success. It only retains the reference
server's stderr and shows it on an unexpected HTTP disconnect.
"""
from pathlib import Path
import argparse

PopenAnchor = "self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)"
GetresponseAnchor = "        resp = conn.getresponse()"
DiagnosticMark = "SHYT_PARITY_DIAGNOSTICS_V43"

def transform(text: str) -> str:
    if DiagnosticMark in text:
        raise ValueError("already patched diagnostic test")
    if text.count(PopenAnchor) != 1 or text.count(GetresponseAnchor) != 1:
        raise ValueError("pinned upstream parity test changed; refusing edit")
    if 'self.log = open(os.path.join(workdir, "shadnet.log"), "wb")' not in text:
        raise ValueError("reference server cleanup anchor changed")
    text = text.replace(
        PopenAnchor,
        '''# SHYT_PARITY_DIAGNOSTICS_V43: retain only disposable local Python backend stderr.
            self.log = open(os.path.join(workdir, "python-backend.log"), "wb")
            self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT)'''
    )
    text = text.replace(
        GetresponseAnchor,
        '''        try:
            resp = conn.getresponse()
        except (OSError, http.client.HTTPException):
            # This log is from a fresh disposable CI fixture, not player data.
            # Stop at 8 KiB to avoid printing unexpected large upstream output.
            path = os.path.join(self.workdir, "python-backend.log")
            if self.kind == "python" and os.path.isfile(path):
                try:
                    if self.log is not None:
                        self.log.flush()
                    with open(path, "rb") as log:
                        tail = log.read()[-8192:]
                    sys.stderr.write("SHYT_PARITY_PYTHON_REFERENCE_FAILURE\\n")
                    sys.stderr.write(tail.decode("utf-8", "replace") + "\\n")
                except OSError:
                    pass
            raise'''
    )
    if text.count(DiagnosticMark) != 1:
        raise ValueError("diagnostic could not be applied exactly once")
    return text


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    args = p.parse_args()
    original = args.source.read_text("utf-8")
    args.source.write_text(transform(original), "utf-8")
    print("SHYT_PARITY_REFERENCE_DIAGNOSTICS_INSTALLED; CTest still fail-closed")


if __name__ == "__main__":
    main()
