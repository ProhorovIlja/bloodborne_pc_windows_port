#!/usr/bin/env python3
"""Native V400: independently verify exact 7 invented function code bytes,
sizes and bbcpu_recomp_hash FNV-1a64 against actual generated RcFunction
table; emit compile-time EXPECTED hash metadata after verification.

NOT a general original Bloodborne 1.09 function-hash parser: bbcpu uses
SPECIAL handling for FS/GS thread-control-block loads, and executable
VA->file offsets are NOT generally identity maps. V400 only accepts the
fully synthetic seven-function ELF built from public invented bytes.
No original game source, commercial data or private hashes in CI.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
PINNED="8f31ec7c41f252730c6325d52647046baef7549f"
IMAGE_SHA256="a87ec8ea0ede452e068c5d6529a88e0759e3738bec917c6624437e10051505af"
MASK=(1<<64)-1
ROWS=re.compile(
    r"\{\s*(0x[0-9a-f]+)\s*,\s*([0-9]+)\s*,\s*"
    r"(0x[0-9a-f]+)ull\s*,\s*f_([0-9a-f]+)\s*,\s*&d_([0-9a-f]+)\s*\}"
)
TABLE=re.compile(r"static const RcFunction table\[\]\s*=\s*\{([\s\S]*?)\};")
FIXED_BYTES=(
    "f0480fb137c3","f30f6f07c3","f30f7f07c3","c5fe6f07c3",
    "c5fe7f07c3","ffd0c3","ffd0c3"
)
FIXED_OFFSETS=("0x1000","0x1020","0x1040","0x1060","0x1080","0x10a0","0x10c0")

def u64(value:object)->int:
    if (not isinstance(value,str) or
        not re.fullmatch(r"0x(?:0|[1-9a-f][0-9a-f]*)",value)):
        raise ValueError("noncanonical uint64 hex")
    x=int(value,16)
    if x>MASK:raise ValueError("uint64 overflow")
    return x

def fnv1a64(code:bytes)->int:
    h=0xcbf29ce484222325
    for byte in code:
        h=((h^byte)*0x100000001b3)&MASK
    return h

def load_fixture(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>20000:
        raise ValueError("bounded original-free identity fixture missing")
    f=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(f,dict) or set(f)!={
        "schema_version","scope","upstream_revision","image_sha256",
        "image_base","hash_algorithm","functions"
    } or f["schema_version"]!=1 or f["scope"]!="invented-only" or (
        f["upstream_revision"]!=PINNED) or f["image_sha256"]!=IMAGE_SHA256 or (
        f["image_base"]!="0x400000") or (
        f["hash_algorithm"]!="bbcpu_recomp_hash_fnv1a64_no_tcb"):
        raise ValueError("untrusted function-identity manifest provenance")
    rows=f["functions"]
    if not isinstance(rows,list) or len(rows)!=7:
        raise ValueError("expected exactly seven invented function identities")
    for i,row in enumerate(rows):
        if not isinstance(row,dict) or set(row)!={
            "offset","code_hex","size","expected_hash"
        } or row["offset"]!=FIXED_OFFSETS[i] or (
            row["code_hex"]!=FIXED_BYTES[i]) or (
            row["size"]!=len(FIXED_BYTES[i])//2 or
            isinstance(row["size"],bool)
        ) or u64(row["expected_hash"])!=fnv1a64(bytes.fromhex(FIXED_BYTES[i])):
            raise ValueError("function bytes, size or independent hash differs")
    return f

def verify(f:dict,image:bytes,source:str)->list[dict]:
    if len(image)!=0x1200 or hashlib.sha256(image).hexdigest()!=f["image_sha256"]:
        raise ValueError("synthetic image identity SHA256 mismatch")
    if image[:4]!=b"\x7fELF" or image[4]!=2 or image[5]!=1:
        raise ValueError("not the known 64-bit little endian synthetic ELF")
    m=TABLE.search(source)
    if not m or len(TABLE.findall(source))!=1:
        raise ValueError("missing/duplicate genuine compiler function table")
    # Any table row not exactly recognized is a hard failure (no silent
    # skipping compiler structs, table aliases or raw guest address data).
    raw=re.findall(r"\{[^{}]*\}",m.group(1))
    if len(raw)!=7:
        raise ValueError("compiled RcFunction count not independently verified")
    output=[]
    for i,(text,entry) in enumerate(zip(raw,f["functions"])):
        row=ROWS.fullmatch(text)
        if not row:raise ValueError("unrecognized compiler RcFunction field schema")
        off,size,h,fn,direct=row.groups()
        expected=u64(entry["offset"])
        code=bytes.fromhex(entry["code_hex"])
        if int(off,16)!=expected or int(size)!=len(code) or (
            int(h,16)!=u64(entry["expected_hash"])) or (
            fn!=f"{expected:x}" or direct!=fn):
            raise ValueError("compiled function address/size/hash/direct identity mismatch")
        if expected+len(code)>len(image) or (
            image[expected:expected+len(code)]!=code):
            raise ValueError("original invented x86 instruction bytes changed")
        output.append({
            "offset":expected,"size":len(code),"hash":fnv1a64(code)
        })
    if len(output)!=7 or len({o["offset"] for o in output})!=7:
        raise ValueError("incomplete source function identity coverage")
    return output

def render(entries:list[dict])->str:
    rows="\n".join(
        "  {UINT64_C(0x%x), UINT64_C(%d), UINT64_C(0x%x)},"%
        (o["offset"],o["size"],o["hash"]) for o in entries
    )
    return (
        "/* V400: INDEPENDENTLY VERIFIED INVENTED FUNCTION HASHES ONLY.\n"
        " * The build-time synthetic ELF SHA256, exact input bytes and real\n"
        " * pinned upstream compiled RcFunction table were all checked.\n"
        " * NOT original commercial Bloodborne function hashes.\n"
        " */\n#ifndef SHYT_NATIVE_V400_EXPECTED_FUNCTION_HEADER\n"
        "#define SHYT_NATIVE_V400_EXPECTED_FUNCTION_HEADER\n"
        "#include \"native_exact_identity_v400.h\"\n"
        "static const ShytNativeExpectedFunctionV400 shyt_v400_expected[] = {\n"
        +rows+"\n};\n"
        "enum { SHYT_V400_EXPECTED_FUNCTION_COUNT =\n"
        "  sizeof(shyt_v400_expected)/sizeof(shyt_v400_expected[0]) };\n"
        "#endif\n"
    )

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--fixture",type=Path,required=True)
    p.add_argument("--image",type=Path,required=True)
    p.add_argument("--table",type=Path,required=True)
    p.add_argument("--out-header",type=Path,required=True)
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location(
        "v390_source_identity",ROOT/"instrument_generated_aot_memory_v390.py")
    if spec is None or spec.loader is None:
        raise ValueError("missing independent pinned compiler identity checker")
    v390=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v390)
    v390.verify_generator(a.upstream_checkout)
    f=load_fixture(a.fixture)
    if (a.image.is_symlink() or not a.image.is_file() or
        a.table.is_symlink() or not a.table.is_file() or
        a.table.name!="recomp.c" or
        a.image.stat().st_size!=0x1200 or
        a.table.stat().st_size>500000 or
        a.out_header.suffix!=".h" or a.out_header.exists() or
        not a.out_header.parent.is_dir() or a.out_header.parent.is_symlink()):
        raise ValueError("unsafe/missing original-free input or preexisting output")
    if any((root/".git").exists()
           for root in (a.out_header.parent,*a.out_header.parent.parents)):
        raise ValueError("attested compiler header must be runner-local")
    entries=verify(f,a.image.read_bytes(),a.table.read_text(encoding="utf-8"))
    a.out_header.write_text(render(entries),encoding="utf-8")
    print("NATIVE_V400_SEVEN_INDEPENDENT_SOURCE_IMAGE_FUNCTION_HASHES_PASS")
    print("validated_functions=7 hash_algorithm=FNV1A64_no_tcb compiled_table_equality=TRUE")
    print("original_game_function_hashes_verified=FALSE original_game_boot=FALSE")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,UnicodeError,RuntimeError,
            subprocess.CalledProcessError) as e:
        print("NATIVE_V400_INDEPENDENT_IDENTITY_REFUSED: "+
              type(e).__name__+": "+str(e)[:180],file=sys.stderr)
        raise SystemExit(2)
