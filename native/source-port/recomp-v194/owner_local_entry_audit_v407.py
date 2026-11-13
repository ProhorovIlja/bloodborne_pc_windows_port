#!/usr/bin/env python3
"""Owner-local, read-only ELF64/x86-64 entrypoint triage (Python 3 + Capstone 5).

Usage: python owner_local_entry_audit_v407.py /path/to/decrypted/elf
Reports counts only. Never executes input, writes files or uses a network.
Direct-edge reachability is an approximation, NOT a native boot proof.
"""
import argparse
from collections import Counter, deque
import json
import mmap
import struct
import sys

import capstone as cs
from capstone.x86_const import X86_OP_IMM

EH = struct.Struct("<16sHHIQQQIHHHHHH")
PH = struct.Struct("<IIQQQQQQ")
LIMIT = 1 << 64


def inspect(image, budget):
    if len(image) < EH.size:
        raise ValueError("truncated ELF header")
    ident, kind, arch, version, entry, phoff, _, _, ehsize, entsize, n, *_ = EH.unpack_from(image)
    if (ident[:7] != b"\x7fELF\x02\x01\x01" or arch != 62 or version != 1
            or kind not in (2, 3, 0xfe00, 0xfe01, 0xfe04, 0xfe10, 0xfe18)
            or ehsize != EH.size or entsize != PH.size or not 0 < n <= 256
            or phoff < EH.size or phoff + n * PH.size > len(image)):
        raise ValueError("expected supported little-endian x86-64 ELF; SELF wrappers are not accepted")
    loads, executable, metadata = [], [], Counter()
    for i in range(n):
        t, flags, off, va, _, file_size, mem_size, _ = PH.unpack_from(image, phoff+i*PH.size)
        if t in (2, 7, 0x61000000):
            metadata[{2:"dynamic_headers", 7:"tls_headers", 0x61000000:"sce_dynlib_headers"}[t]] += 1
        if t != 1:
            continue
        if file_size > mem_size or off+file_size > len(image) or va+mem_size > LIMIT:
            raise ValueError("invalid PT_LOAD bounds")
        if mem_size:
            loads.append((va,va+mem_size))
        if flags & 1 and file_size:
            executable.append((va,va+file_size,off))
    loads.sort()
    if any(a[1]>b[0] for a,b in zip(loads,loads[1:])):
        raise ValueError("overlapping PT_LOAD mappings")
    if not any(start <= entry < end for start,end,_ in executable):
        raise ValueError("entry is outside file-backed executable memory")

    dis = cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64)
    dis.detail = True
    todo, queued = deque([entry]), {entry}
    starts, covered, counts = set(), {}, Counter()

    def enqueue(target):
        if target not in queued:
            todo.append(target)
            queued.add(target)

    while todo and counts["visited_locations"] < budget:
        ip = todo.popleft()
        counts["visited_locations"] += 1
        if ip in covered and covered[ip] != ip:
            counts["overlapping_decode_targets"] += 1
            continue
        span = next((s for s in executable if s[0] <= ip < s[1]), None)
        if span is None:
            counts["non_file_backed_targets"] += 1
            continue
        start,end,off = span
        pos = off + ip-start
        ins = next(dis.disasm(image[pos:pos+min(15,end-ip)],ip,count=1),None)
        if ins is None:
            counts["decode_failures"] += 1
            continue
        if any(a in covered for a in range(ip,ip+ins.size)):
            counts["overlapping_decode_targets"] += 1
            continue
        starts.add(ip)
        covered.update((a,ip) for a in range(ip,ip+ins.size))
        next_ip = ip+ins.size
        op = ins.mnemonic
        if ins.group(cs.CS_GRP_INT) or ins.group(cs.CS_GRP_IRET) or op in {
            "syscall","sysenter","sysret","sysexit","hlt","ud0","ud1","ud2","xbegin","xabort",
            "lcall","ljmp","retf","retfq","rsm","vmcall","vmmcall"
        }:
            counts["system_or_unsupported_transfers"] += 1
        elif ins.group(cs.CS_GRP_RET):
            counts["returns"] += 1
        elif ins.group(cs.CS_GRP_CALL) or ins.group(cs.CS_GRP_JUMP) or op.startswith("loop"):
            call = ins.group(cs.CS_GRP_CALL)
            direct = len(ins.operands) == 1 and ins.operands[0].type == X86_OP_IMM
            counts[("direct_" if direct else "indirect_")+("calls" if call else "branches")] += 1
            if direct:
                enqueue(ins.operands[0].imm % LIMIT)
            if call or op != "jmp":
                enqueue(next_ip)  # Assume calls can return; do not resolve indirect targets.
        else:
            enqueue(next_ip)
    return {
        "scope":"owner-local direct-edge startup triage",
        "executable_file_segments":len(executable),
        "loader_metadata":dict(metadata),
        "decoded_instructions":len(starts),
        "counts":dict(counts),
        "budget_exhausted":bool(todo),
        "pending_locations":len(todo),
        "retail_native_boot_proven":False,
    }


def self_test():
    base, off = 0x401000, 0x100
    # call +3; call rax; ret; syscall. The direct call lands on syscall.
    code = bytes.fromhex("e803000000 ffd0 c3 0f05")
    ident = b"\x7fELF\x02\x01\x01"+b"\0"*9
    head = EH.pack(ident,2,62,1,base,EH.size,0,0,EH.size,PH.size,1,0,0,0)
    ph = PH.pack(1,5,off,base,base,len(code),len(code),0x1000)
    image = (head+ph).ljust(off,b"\0")+code
    r = inspect(image,100)
    for k in ("direct_calls","indirect_calls","returns","system_or_unsupported_transfers"):
        if r["counts"].get(k) != 1:
            raise ValueError("self-test edge classification failed")
    if r["budget_exhausted"] or not inspect(image,1)["budget_exhausted"]:
        raise ValueError("self-test budget handling failed")
    for invalid in (image[:10],image[:-1],b"SELF"+image[4:]):
        try:
            inspect(invalid,100)
        except ValueError:
            continue
        raise ValueError("self-test invalid input was accepted")
    print("NATIVE_V407_OWNER_LOCAL_ENTRY_AUDIT_SELF_TEST_PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("elf",nargs="?")
    p.add_argument("--max-instructions",type=int,default=20000)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if not 1<=a.max_instructions<=250000 or bool(a.elf)==a.self_test:
        p.error("choose an ELF or --self-test; budget must be 1–250000")
    try:
        if a.self_test:
            self_test()
        else:
            with open(a.elf,"rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as image:
                print(json.dumps(inspect(image,a.max_instructions),indent=2,sort_keys=True))
    except (OSError,ValueError,cs.CsError) as e:
        # Never echo an owner-local path (including from an OS exception).
        print("audit refused: "+(str(e) if type(e) is ValueError else "input or decoder unavailable"),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
