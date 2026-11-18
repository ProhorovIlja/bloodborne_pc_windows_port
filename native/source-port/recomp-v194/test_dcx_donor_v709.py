# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare valid DFLT and safe malformed cases with a local Openborne undcx."""
import argparse
from pathlib import Path
from random import Random
import subprocess
from tempfile import TemporaryDirectory
import zlib

from dcx_dflt_v708 import VARIANTS, unpack
from test_dcx_dflt_v708 import container


def run(exe):
    rng = Random(709)
    counts = dict(exact=0, excess_size=0, trailing=0, bad_adler=0)
    with TemporaryDirectory(prefix='bb709-') as tmp:
        path = Path(tmp) / 'case.dcx'

        def donor(data):
            path.write_bytes(data)
            return subprocess.run([exe, path], capture_output=True, timeout=5)

        for i in range(1, 65):
            raw = rng.randbytes(i * 29) if i % 2 else b'BND4' * i
            stream = zlib.compress(raw)
            for variant in sorted(VARIANTS):
                good = container(stream, len(raw), variant)
                ref = donor(good)
                if ref.returncode or ref.stdout != raw or unpack(good, max_output=len(raw)) != raw:
                    raise AssertionError('valid DCX mismatch')
                counts['exact'] += 1
                for key, bad in (
                    ('excess_size', container(stream, len(raw)+1, variant)),
                    ('trailing', good+b'x'),
                    ('bad_adler', container(stream[:-1]+bytes([stream[-1]^1]), len(raw), variant)),
                ):
                    try:
                        unpack(bad, max_output=len(raw)+1)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(f'strict reader accepted {key}')
                    ref = donor(bad)
                    if not ref.returncode:
                        counts[key] += 1
                        expected = raw+b'\0' if key == 'excess_size' else raw
                        if ref.stdout != expected or key == 'bad_adler':
                            raise AssertionError(f'unexpected donor output: {key}')
    print(counts)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('undcx', type=Path)
    run(p.parse_args().undcx.resolve())
