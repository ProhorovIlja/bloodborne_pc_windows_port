#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V7: synthetic Ed25519-signed upstream ZIP fixtures, NO Bloodborne files."""
from pathlib import Path
import hashlib
import tempfile
import zipfile
from nacl.signing import SigningKey
from assemble_verified_upstream_bbhost_v7 import (
    ARCHIVE_NAME, ReleaseRejected, install_verified_bbhost_v7
)


def rejected(task):
    try:
        task()
    except ReleaseRejected:
        return
    raise AssertionError("Tampering or unsafe ZIP was accepted")


def main():
    with tempfile.TemporaryDirectory(prefix="shyt-bbhost-v7-fake-") as tmp:
        base=Path(tmp)
        pub=SigningKey(b"\x19"*32)
        key=pub.verify_key.encode()
        package=base/ARCHIVE_NAME
        sums=base/"SHA256SUMS"
        signature=base/"SHA256SUMS.sig"
        launcher=base/"YT GUI"
        launcher.mkdir()
        (launcher/"BLauncher.exe").write_bytes(b"MZ"+b"fake launcher"*7000)
        def make_zip(members):
            with zipfile.ZipFile(package,"w",compression=zipfile.ZIP_STORED) as z:
                for name,body in members:
                    z.writestr(name,body)
            body=(hashlib.sha256(package.read_bytes()).hexdigest()+
                  "  "+ARCHIVE_NAME+"\n").encode()
            sums.write_bytes(body)
            signature.write_bytes(pub.sign(body).signature)

        valid=[("bbhost-win-v0.2.24/bbhost.exe",b"MZ"+b"f"*74000),
               ("bbhost-win-v0.2.24/data/config.toml",b"[online]\n"),
               ("bbhost-win-v0.2.24/LICENSE",b"synthetic GPL notice")]
        make_zip(valid)
        package.write_bytes(package.read_bytes()+b"x")
        rejected(lambda:install_verified_bbhost_v7(package,sums,signature,launcher,key))
        make_zip(valid)
        signature.write_bytes(b"z"*64)
        rejected(lambda:install_verified_bbhost_v7(package,sums,signature,launcher,key))
        make_zip(valid)
        rejected(lambda:install_verified_bbhost_v7(package,sums,signature,launcher))
        make_zip([("../bbhost.exe",b"MZ"+b"x"*80000)])
        rejected(lambda:install_verified_bbhost_v7(package,sums,signature,launcher,key))
        make_zip([("bbhost.exe",b"MZ"+b"x"*80000),
                  ("BBHOST.EXE",b"MZ"+b"x"*80000)])
        rejected(lambda:install_verified_bbhost_v7(package,sums,signature,launcher,key))
        make_zip(valid)
        install_verified_bbhost_v7(package,sums,signature,launcher,key)
        assert (launcher/"bbhost"/"bbhost.exe").read_bytes()[:2]==b"MZ"
        assert (launcher/"bbhost"/"data"/"config.toml").is_file()
        assert (launcher/"bbhost"/"SHYT-EXPERIMENTAL.txt").is_file()
        assert (launcher/"BLauncher.exe").is_file()
        rejected(lambda:install_verified_bbhost_v7(package,sums,signature,launcher,key))
    print("SHYT_BBHOST_V7_SIGNED_RELEASE_TAMPERED_ARCHIVE_AND_ROLLBACK_GATES_PASS")


if __name__=="__main__":
    main()
