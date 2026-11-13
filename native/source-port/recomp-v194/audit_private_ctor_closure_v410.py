#!/usr/bin/env python3
"""Private SCE legacy constructor plan vs. caller-supplied native binding IDs.

--cursor is the audited initial cursor BEFORE its first decrement.
IDs are ELF virtual addresses, without a loader slide. --bindings accepts
one integer per line (Python base-0), or is omitted for an empty baseline.
A match tests presence only, not function identity, provenance or execution.
No constructor address, image bytes, hash or path is printed.
"""
import argparse
import hashlib
import json
import mmap
import struct
import sys
from pathlib import Path

import verify_generated_coverage_v207 as coverage

EH = struct.Struct("<16sHHIQQQIHHHHHH")
PH = struct.Struct("<IIQQQQQQ")
MASK = (1 << 64) - 1
MAX_CTORS = 65536


def legacy_plan(image, cursor):
    def require(ok, why):
        if not ok:
            raise ValueError(why)

    require(len(image) >= EH.size, "truncated ELF")
    ident, kind, arch, ver, _, off, _, _, eh, ph, count, *_ = EH.unpack_from(image)
    require(ident[:7] == b"\x7fELF\x02\x01\x01" and arch == 62 and ver == 1
            and kind in (0xfe00, 0xfe01, 0xfe04, 0xfe10, 0xfe18)
            and eh == EH.size and ph == PH.size and 0 < count <= 256
            and off >= eh and off + count * ph <= len(image), "unsupported SCE ELF")
    loads, meta = [], {}
    for i in range(count):
        t, flags, pos, va, _, size, mem, _ = PH.unpack_from(image, off + i*ph)
        if t not in (1, 2, 0x61000000):
            continue
        require(pos + size <= len(image), "segment out of file bounds")
        if t == 1:
            require(size <= mem and va + mem <= MASK+1, "invalid load segment")
            if mem:
                loads.append((va, va+mem, va+size, pos, flags))
        else:
            require(t not in meta, "duplicate metadata segment")
            meta[t] = (pos, size)
    loads.sort()
    require(all(a[1] <= b[0] for a,b in zip(loads,loads[1:])), "overlapping loads")
    require(2 in meta and 0x61000000 in meta, "SCE relocation metadata missing")
    do, ds = meta[2]
    bo, bs = meta[0x61000000]
    require(0 < ds <= 262144 and ds % 16 == 0, "invalid dynamic table length")
    tags = {}
    keys = {0x61000029, 0x6100002d, 0x6100002f, 0x61000031}
    for pos in range(do, do+ds, 16):
        t,v = struct.unpack_from("<QQ",image,pos)
        if not t:
            break
        if t in keys:
            require(t not in tags, "duplicate relocation tag")
            tags[t] = v
    else:
        raise ValueError("dynamic terminator missing")
    rel = {}
    for addr,size in ((0x61000029,0x6100002d),(0x6100002f,0x61000031)):
        if addr not in tags and size not in tags:
            continue
        a,z = tags.get(addr),tags.get(size)
        require(a is not None and z is not None and z % 24 == 0
                and z <= 24*2000000 and a+z <= bs, "invalid relocation span")
        for pos in range(bo+a,bo+a+z,24):
            slot,info,add = struct.unpack_from("<QQq",image,pos)
            require(slot not in rel, "duplicate relocation destination")
            rel[slot]=(info,add)
    require(8 <= cursor <= MASK and cursor % 8 == 0, "invalid initial cursor")
    segment = next((p for p in loads if p[0] <= cursor-8 and cursor <= p[2]),None)
    require(segment is not None, "constructor cursor is not file backed")
    base,_,_,file_off,_ = segment
    targets, empty = [],0
    for _ in range(MAX_CTORS):
        cursor -= 8
        require(cursor >= base,"legacy sentinel not found in segment")
        raw, = struct.unpack_from("<Q",image,file_off+cursor-base)
        fix = rel.get(cursor)
        if fix is None:
            if raw == MASK:
                return targets,empty
            require(raw == 0, "nonempty unrelocated constructor slot")
            empty += 1
            continue
        info,add = fix
        require(info == 8 and any(a <= add < z and flags & 1
                                  for a,_,z,_,flags in loads),
                "constructor relocation is not a file-backed executable relative target")
        targets.append(add)
    raise ValueError("legacy slot budget exhausted")


def compare(targets, empty, bindings):
    missing = [i for i,x in enumerate(targets,1) if x not in bindings]
    return dict(ordered_callbacks=len(targets), distinct_targets=len(set(targets)),
                null_slots_skipped=empty, matching_entries=len(targets)-len(missing),
                unmatched_entries=len(missing),
                first_unmatched_ordinal=missing[0] if missing else None,
                binding_presence_only=True, retail_boot_proven=False)


def generated_ids(image, work):
    """V204 source registration, NOT an attested linked native registry."""
    root=Path(work)
    paths=[root/"full-original-preparation.json", root/"scan/functions.tsv",
           root/"generated/recomp.c"]
    limits=[32*1024*1024,coverage.MAX_INDEX_BYTES,coverage.MAX_TABLE_BYTES]
    for p,limit in zip(paths,limits):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>limit:
            raise ValueError("unsafe V204 input")
    manifest=json.loads(paths[0].read_bytes())
    index_bytes=paths[1].read_bytes()
    table_bytes=paths[2].read_bytes()
    if (manifest.get("format")!="SHYT_PRIVATE_FULL_IMAGE_V204" or
        manifest.get("upstream")!="8f31ec7c41f252730c6325d52647046baef7549f" or
        manifest.get("original_size_bytes")!=len(image) or
        manifest.get("input_sha256")!=hashlib.sha256(image).hexdigest() or
        manifest.get("scanner_index_sha256")!=hashlib.sha256(index_bytes).hexdigest() or
        manifest.get("c_hashes",{}).get("recomp.c")!=hashlib.sha256(table_bytes).hexdigest()):
        raise ValueError("V204 provenance mismatch")
    index=coverage.scan_index(paths[1])
    if hashlib.sha256(paths[1].read_bytes()).digest()!=hashlib.sha256(index_bytes).digest():
        raise ValueError("scanner index changed")
    table=table_bytes.decode("utf-8")
    report=coverage.count_table(table,manifest.get("functions_scanned"),index)
    if any(manifest.get(k)!=v for k,v in report.items()):
        raise ValueError("V204 registration report mismatch")
    ids=set()
    begun=False
    for line in table.splitlines():
        if not begun:
            begun=bool(coverage.HEADER.fullmatch(line))
        elif line.strip()=="};":
            break
        else:
            ids.add(int(coverage.ENTRY.fullmatch(line)[1],16))
    return ids


def self_test():
    start, cursor = 0x4000,0x4030
    ident = b"\x7fELF\x02\x01\x01"+bytes(9)
    data = bytearray(1024)
    EH.pack_into(data,0,ident,0xfe10,62,1,start,EH.size,0,0,EH.size,PH.size,3,0,0,0)
    for i,row in enumerate(((1,5,256,start,start,64,64,8),
                            (2,4,384,0,0,48,48,8),
                            (0x61000000,4,512,0,0,72,72,8))):
        PH.pack_into(data,EH.size+i*PH.size,*row)
    struct.pack_into("<6Q",data,384,0x6100002f,0,0x61000031,72,0,0)
    struct.pack_into("<Q",data,256+8,MASK)
    for i,(slot,add) in enumerate(((cursor-8,start+2),(cursor-24,start+1),
                                   (cursor-32,start+2))):
        struct.pack_into("<QQq",data,512+24*i,slot,8,add)
    # cursor itself is not visited; empty cursor-16 is skipped.
    out,empty=legacy_plan(data,cursor)
    if out != [start+2,start+1,start+2] or empty != 1:
        raise RuntimeError("incorrect traversal")
    report=compare(out,empty,{start+2})
    if report["first_unmatched_ordinal"]!=2 or report["matching_entries"]!=2:
        raise RuntimeError("incorrect binding comparison")
    for offset,value in ((392,80),(520,7),(528,start+64),(264,3)):
        bad=bytearray(data)
        struct.pack_into("<Q",bad,offset,value)
        try:
            legacy_plan(bad,cursor)
        except ValueError:
            continue
        raise RuntimeError("malformed input accepted")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        (p/"generated").mkdir()
        (p/"scan").mkdir()
        scan=b"address\tsize\tinstructions\tundecodable\n0x4001\t3\t1\t0\n0x4002\t3\t1\t0\n"
        table=b"static const RcFunction table[] = {\n{0x4002, 3, 0x9ull, f_4002, &d_4002},\n};\n"
        (p/"generated/recomp.c").write_bytes(table)
        (p/"scan/functions.tsv").write_bytes(scan)
        meta=dict(format="SHYT_PRIVATE_FULL_IMAGE_V204",
                  upstream="8f31ec7c41f252730c6325d52647046baef7549f",
                  original_size_bytes=len(data), input_sha256=hashlib.sha256(data).hexdigest(),
                  scanner_index_sha256=hashlib.sha256(scan).hexdigest(),
                  c_hashes={"recomp.c":hashlib.sha256(table).hexdigest()},
                  **coverage.count_table(table.decode(),2))
        (p/"full-original-preparation.json").write_text(json.dumps(meta))
        if generated_ids(data,p)!={start+2}:
            raise RuntimeError("wrong V204 source baseline")
        (p/"generated/recomp.c").write_bytes(table+b" ")
        try:
            generated_ids(data,p)
        except ValueError:
            pass
        else:
            raise RuntimeError("changed V204 table was accepted")
    print("NATIVE_V410_LEGACY_CTOR_CLOSURE_PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("elf",nargs="?")
    p.add_argument("--cursor",type=lambda v:int(v,0))
    inputs=p.add_mutually_exclusive_group()
    inputs.add_argument("--bindings")
    inputs.add_argument("--v204-work",help="compare hash-matched generated source registrations")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test and not a.elf and a.cursor is None and not a.bindings and not a.v204_work:
        self_test()
        return 0
    if a.self_test or not a.elf or a.cursor is None:
        p.error("choose --self-test, or specify ELF and --cursor")
    bindings=set()
    try:
        if a.bindings:
            with open(a.bindings,"rb") as rows:
                for i in range(2000001):
                    row=rows.readline(65)
                    if not row:
                        break
                    if len(row)>64 or i==2000000:
                        raise ValueError("binding input budget exceeded")
                    key=int(row.strip(),0)
                    if not 0 <= key <= MASK or key in bindings:
                        raise ValueError("invalid or duplicate binding ID")
                    bindings.add(key)
    except (OSError,ValueError):
        print("binding input refused",file=sys.stderr)
        return 2
    try:
        with open(a.elf,"rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as image:
            targets,empty=legacy_plan(image,a.cursor)
            if a.v204_work:
                bindings=generated_ids(image,a.v204_work)
    except (OSError,ValueError,TypeError,AttributeError,struct.error):
        print("ELF or constructor plan refused",file=sys.stderr)
        return 2
    report=compare(targets,empty,bindings)
    report["binding_baseline_supplied"]=bool(a.bindings or a.v204_work)
    report["baseline_kind"]=("v204_generated_source" if a.v204_work else
                             "provided_ids" if a.bindings else "none")
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main())
