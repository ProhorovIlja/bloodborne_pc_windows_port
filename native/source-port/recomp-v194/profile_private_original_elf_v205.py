#!/usr/bin/env python3
"""V205: PRIVATE REAL PS4 ELF64 full-image metadata profiler, stdlib only.

Input is a locally supplied user-owned decrypted game ELF. It does not
decode/distribute game instructions, read asset text, load PS4 code, or
upload anything. Reads ORIGINAL PS4 linker relocation table and
original DWARF unwind FDE ranges directly; reports aggregate counts
only. This is more informative than artificial 5-function test fixtures,
but not the same as full control-flow discovery or a playable port.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import struct
import sys

PS4_ELF_TYPE=0xFE10
PT_LOAD=1
PT_DYNAMIC=2
PT_GNU_EH_FRAME=0x6474E550
PT_SCE_DYNLIBDATA=0x61000000
MAX_BYTES=512*1024*1024

def profile(path:Path)->dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("private original x86-64 ELF input is missing or a symlink")
    if not 1000000<=path.stat().st_size<=MAX_BYTES:
        raise ValueError("unexpected original executable size")
    data=path.read_bytes()
    if len(data)<64 or data[:7]!=b"\x7fELF\x02\x01\x01":
        raise ValueError("decrypted PS4 ELF64 (not encrypted SELF) required")
    elf_type, machine=struct.unpack_from("<HH",data,16)
    if elf_type!=PS4_ELF_TYPE or machine!=62:
        raise ValueError("PS4 x86-64 ELF executable type required")

    def region(offset:int,n:int):
        if offset<0 or n<0 or offset+n>len(data):
            raise ValueError("ELF range outside private original file")
        return memoryview(data)[offset:offset+n]

    phoff=struct.unpack_from("<Q",data,32)[0]
    entsize=struct.unpack_from("<H",data,54)[0]
    nph=struct.unpack_from("<H",data,56)[0]
    if entsize!=56 or not 1<=nph<=256:
        raise ValueError("invalid PS4 ELF program headers")
    region(phoff,entsize*nph)
    segments=[struct.unpack_from("<IIQQQQQQ",data,phoff+i*entsize)
              for i in range(nph)]
    def exact_segment(kind:int):
        matches=[s for s in segments if s[0]==kind]
        if len(matches)!=1:
            raise ValueError("required PS4 ELF segment unavailable")
        region(matches[0][2],matches[0][5])
        return matches[0]
    eh=exact_segment(PT_GNU_EH_FRAME)
    ld=exact_segment(PT_SCE_DYNLIBDATA)
    dyn=exact_segment(PT_DYNAMIC)
    exec_segs=[s for s in segments if s[0]==PT_LOAD and s[1]&1]
    if not exec_segs:raise ValueError("original executable code segment missing")
    def in_code(a):
        return any(s[3]<=a<s[3]+s[5] for s in exec_segs)

    eoff,eva,esize=eh[2],eh[3],eh[5]
    version,ptrenc,countenc,tableenc=struct.unpack_from("<BBBB",data,eoff)
    if (version,ptrenc,countenc,tableenc)!=(1,0x1b,0x03,0x3b):
        raise ValueError("unsupported original DWARF .eh_frame_hdr encodings")
    fdes=struct.unpack_from("<I",data,eoff+8)[0]
    if fdes>1000000 or 12+8*fdes>esize:
        raise ValueError("unbounded or truncated original FDE table")
    starts=[]
    ranges=[]
    invalid=0
    for i in range(fdes):
        func_delta,fde_delta=struct.unpack_from("<ii",data,eoff+12+i*8)
        start=eva+func_delta
        fde_va=eva+fde_delta
        offs=[s[2]+fde_va-s[3] for s in segments
              if s[0]==PT_LOAD and s[3]<=fde_va and fde_va+16<=s[3]+s[5]]
        if len(offs)!=1:raise ValueError("unmapped original FDE address")
        flen,cie_offset,initial_delta,length=struct.unpack_from(
            "<IIiI",data,offs[0])
        if not 12<=flen<=65536 or not length or start!=fde_va+8+initial_delta:
            invalid+=1
        if not in_code(start) or not in_code(start+length-1):
            invalid+=1
        starts.append(start)
        ranges.append((start,start+length))
    if starts!=sorted(set(starts)):
        raise ValueError("original unwind entries not sorted and unique")
    overlaps=sum(a[1]>b[0] for a,b in zip(ranges,ranges[1:]))
    if invalid or overlaps:
        raise ValueError("malformed original unwind function ranges")

    dynamic=[]
    for pos in range(dyn[2],dyn[2]+dyn[5],16):
        tag,val=struct.unpack_from("<QQ",data,pos)
        if not tag:break
        dynamic.append((tag,val))
    tags=dict(dynamic)
    def linker_slice(off,size):
        if off<0 or size<0 or off+size>ld[5]:
            raise ValueError("PS4 dynamic linker metadata out of bounds")
        return region(ld[2]+off,size)
    symdata=linker_slice(tags[0x61000039],tags[0x6100003f])
    if len(symdata)%24:raise ValueError("invalid symbol table")
    symbols=len(symdata)//24
    undefined=0
    for i in range(symbols):
        rec=struct.unpack_from("<IBBHQQ",symdata,i*24)
        if rec[3]==0:undefined+=1

    kinds=collections.Counter()
    code_relative=set()
    relative_total=0
    indirect_slots=0
    for poskey,lenkey in ((0x61000029,0x6100002d),
                          (0x6100002f,0x61000031)):
        reloc=linker_slice(tags[poskey],tags[lenkey])
        if len(reloc)%24:raise ValueError("invalid PS4 relocation table")
        for j in range(0,len(reloc),24):
            target,info,addend=struct.unpack_from("<QQq",reloc,j)
            kind,idx=info&0xffffffff,info>>32
            if idx>=symbols:raise ValueError("invalid imported symbol index")
            kinds[kind]+=1
            if kind==8 and in_code(addend):
                relative_total+=1
                code_relative.add(addend)
            if kind in (6,7):indirect_slots+=1
    return {
        "format":"shyt-native-real-original-elf-profile-v205",
        "decrypted_original_ps4_x86_64_elf":True,
        "private_original_elf_bytes":len(data),
        "code_segment_bytes":sum(s[5] for s in exec_segs),
        "elf_program_headers":nph,
        "unwind_fde_functions":fdes,
        "unwind_function_ranges_nonoverlapping":True,
        "unwind_function_bytes_total":sum(b-a for a,b in ranges),
        "ps4_dynamic_entries":len(dynamic),
        "ps4_dynamic_symbols":symbols,
        "undefined_dynamic_symbols":undefined,
        "relocations_by_kind":dict(sorted(kinds.items())),
        "relocations_total":sum(kinds.values()),
        "relative_relocations_into_executable_code":relative_total,
        "distinct_relative_code_pointer_targets":len(code_relative),
        "import_jump_or_data_slots":indirect_slots,
        "entire_original_code_recompiled":False,
        "original_version_109_cryptographically_verified":False,
        "real_game_booted":False,
        "proprietary_game_code_exported":False
    }

if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--decrypted-elf",required=True,type=Path)
    args=a.parse_args()
    try:
        result=profile(args.decrypted_elf)
    except (OSError,ValueError,KeyError,struct.error) as e:
        # No raw source bytes, symbols, function addresses, or names printed.
        print("V205 private original ELF metadata profile blocked: "
              +str(e)[:160],file=sys.stderr)
        raise SystemExit(2)
    print("SHYT_NATIVE_V205_GENUINE_PRIVATE_FULL_ORIGINAL_ELF_METADATA_PASS")
    print(json.dumps(result,sort_keys=True))
