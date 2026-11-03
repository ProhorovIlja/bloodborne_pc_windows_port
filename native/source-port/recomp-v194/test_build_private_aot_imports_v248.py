#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V248 synthetic import fixtures only: verifies private build boundary."""
from __future__ import annotations
from pathlib import Path
import os
import subprocess
import sys
import tempfile

import build_private_aot_imports_v248 as builder


def checked_failure(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("unsafe input was accepted")


def main():
    assert len(builder.MATH_NAMES)==23
    assert len(builder.CLOCK_NAMES)==2
    names=builder.MATH_NAMES+builder.CLOCK_NAMES
    rows=["stub\tname"]
    rows.extend(f"0x{0x100+i*16:x}\t{name}" for i,name in enumerate(names))
    source="\n".join(rows)+"\n"
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        imports=root/"imports.tsv"
        private=root/"derived-private"
        private.mkdir()
        output=private/"imports_v248.c"
        imports.write_text(source,encoding="utf-8")
        parsed=builder.read_original_imports(imports)
        assert set(parsed)==set(names)
        generated=builder.generate_source(parsed)
        assert "shyt_private_aot_imports_v248_init" in generated
        assert "shyt_math_import_table_v224_init" in generated
        assert "image_base" in generated
        assert "UINT64_C(0x" in generated
        builder.assert_private_output(output)
        cmd=[sys.executable,str(Path(builder.__file__).resolve()),
             "--original-imports",str(imports),"--private-output",str(output)]
        good=subprocess.run(cmd,text=True,capture_output=True,check=False)
        assert good.returncode==0, good.stderr[:250]
        assert "SHYT_V248_PRIVATE_AOT_IMPORTS_READY" in good.stdout
        assert "0x" not in good.stdout and "sceKernel" not in good.stdout
        assert output.is_file() and output.read_text()==generated
        assert output.stat().st_size<8192
        # Refuse overwriting any existing generated private file.
        again=subprocess.run(cmd,text=True,capture_output=True,check=False)
        assert again.returncode != 0
        assert output.read_text()==generated
        # Reject missing clock functions, no guessed PS4 symbols or offsets.
        imports.write_text("\n".join(rows[:-1])+"\n",encoding="utf-8")
        checked_failure(lambda:builder.read_original_imports(imports))
        # Reject duplicate import names and duplicate address slots.
        imports.write_text(source+rows[1]+"\n",encoding="utf-8")
        checked_failure(lambda:builder.read_original_imports(imports))
        imports.write_text(source+f"0x100\textra\n",encoding="utf-8")
        checked_failure(lambda:builder.read_original_imports(imports))
        imports.write_text(source.replace("stub\tname","name\tstub"),encoding="utf-8")
        checked_failure(lambda:builder.read_original_imports(imports))
        imports.write_text(source,encoding="utf-8")
        if os.name!="nt":
            linked=root/"linked-input.tsv"
            linked.symlink_to(imports)
            checked_failure(lambda:builder.read_original_imports(linked))
            linked_out=root/"linked-output.c"
            linked_out.symlink_to(output)
            checked_failure(lambda:builder.assert_private_output(linked_out))
        # Generated code in a Git worktree is prohibited.
        public=root/"public-repo"
        public.mkdir()
        (public/".git").mkdir()
        checked_failure(lambda:builder.assert_private_output(public/"leaked.c"))
        # Full report/gamelogs are not accepted as input.
        imports.write_text(source+"x"*builder.MAX_INDEX_BYTES,encoding="utf-8")
        checked_failure(lambda:builder.read_original_imports(imports))
    print("SHYT_V248_PRIVATE_AOT_IMPORTS_SYNTHETIC_SECURITY_PASS")


if __name__=="__main__":
    main()
