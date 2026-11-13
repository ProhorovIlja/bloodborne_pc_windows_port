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
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

EH = struct.Struct("<16sHHIQQQIHHHHHH")
PH = struct.Struct("<IIQQQQQQ")
LIMIT = 1 << 64


def sce_slots(image, dyn, blob):
    """Return audited SCE slot kinds; never parse or emit symbol names."""
    if not dyn or not blob:
        return {}
    do, ds = dyn
    bo, bs = blob
    if not ds or ds % 16 or ds > 256 * 1024:
        raise ValueError("invalid SCE dynamic table size")
    keys = {0x61000029, 0x6100002d, 0x6100002f, 0x61000031}
    tags = {}
    for pos in range(do, do + ds, 16):
        tag, value = struct.unpack_from("<QQ", image, pos)
        if tag == 0:
            break
        if tag in keys:
            if tag in tags and tags[tag] != value:
                raise ValueError("conflicting SCE relocation tags")
            tags[tag] = value
    else:
        raise ValueError("unterminated SCE dynamic table")
    slots = {}
    for address, size in ((0x61000029, 0x6100002d), (0x6100002f, 0x61000031)):
        if address not in tags and size not in tags:
            continue
        off, length = tags.get(address), tags.get(size)
        if (off is None or length is None or length % 24 or
                length > 24 * 250000 or off + length > bs):
            raise ValueError("invalid SCE relocation range")
        for pos in range(bo + off, bo + off + length, 24):
            target, info, _ = struct.unpack_from("<QQq", image, pos)
            kind = info & 0xffffffff
            if kind in (6, 7) and info >> 32:
                if target in slots and slots[target] != info:
                    raise ValueError("conflicting SCE slot relocations")
                slots[target] = info
    return slots


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
    dynamic = blob = None
    for i in range(n):
        t, flags, off, va, _, file_size, mem_size, _ = PH.unpack_from(image, phoff+i*PH.size)
        if t in (2, 7, 0x61000000):
            metadata[{2:"dynamic_headers", 7:"tls_headers", 0x61000000:"sce_dynlib_headers"}[t]] += 1
        if t in (2, 0x61000000):
            if off + file_size > len(image):
                raise ValueError("invalid dynamic metadata range")
            if t == 2:
                if dynamic is not None:
                    raise ValueError("multiple dynamic headers")
                dynamic = (off, file_size)
            else:
                if blob is not None:
                    raise ValueError("multiple SCE dynlib headers")
                blob = (off, file_size)
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

    slots = sce_slots(image, dynamic, blob)
    reached_slots = set()
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
            elif len(ins.operands) == 1 and ins.operands[0].type == X86_OP_MEM:
                operand = ins.operands[0]
                mem = operand.mem
                if (operand.size == 8 and mem.base == X86_REG_RIP and
                        not mem.index and not mem.segment):
                    slot = (next_ip + mem.disp) % LIMIT
                    if slot in slots:
                        reached_slots.add(slot)
                        counts["relocation_backed_indirect_calls" if call else
                               "relocation_backed_indirect_branches"] += 1
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
        "sce_relocation_backed_slots":len(slots),
        "reachable_sce_relocation_backed_slots":len(reached_slots),
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
    # Direct call -> RIP-relative tail thunk backed by a SCE JUMP_SLOT.
    # A second, register-indirect call must remain unclassified.
    code = bytes.fromhex("e803000000 ffd0 c3 ff2512000000")
    dynoff, bloboff = 0x180, 0x1c0
    dynamic = b"".join(struct.pack("<QQ", k, v) for k,v in
                       ((0x61000029,0),(0x6100002d,24),(0,0)))
    reloc = struct.pack("<QQq", base+0x20, (1<<32)|7, 0)
    head = EH.pack(ident,0xfe10,62,1,base,EH.size,0,0,EH.size,PH.size,3,0,0,0)
    phs = b"".join(PH.pack(*p) for p in (
        (1,5,off,base,base,len(code),0x40,0x1000),
        (2,4,dynoff,0,0,len(dynamic),len(dynamic),8),
        (0x61000000,4,bloboff,0,0,len(reloc),len(reloc),8)))
    fixture = ((head+phs).ljust(off,b"\0")+code).ljust(dynoff,b"\0")+dynamic
    fixture = fixture.ljust(bloboff,b"\0")+reloc
    report = inspect(fixture,100)
    if (report["reachable_sce_relocation_backed_slots"] != 1 or
            report["counts"].get("relocation_backed_indirect_branches") != 1 or
            report["counts"].get("relocation_backed_indirect_calls",0) != 0):
        raise ValueError("self-test relocation correlation failed")
    bad = bytearray(fixture)
    struct.pack_into("<Q", bad, dynoff+24, 48)
    try:
        inspect(bad,100)
    except ValueError:
        pass
    else:
        raise ValueError("self-test invalid relocation span was accepted")
    print("NATIVE_V408_STARTUP_RELOCATION_CORRELATION_PASS")


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
