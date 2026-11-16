#!/usr/bin/env python3
"""Offline RX pointer triage; emits counts, not a code/data classification."""
import argparse
from collections import Counter
from bisect import bisect_right
import json
from pathlib import Path
import struct
from ps4_relocation_audit_v561 import audit


def runs(pairs):
    group = []
    for slot, target in sorted(pairs):
        if group and slot != group[-1][0]+8:
            yield group
            group = []
        group.append((slot, target))
    if group:
        yield group


def thunk_target(buf, va):
    # Strict SysV this-adjustor: add/sub imm8 to RDI; jmp rel32.
    if (len(buf) == 9 and buf[:3] in (b'\x48\x83\xc7', b'\x48\x83\xef')
            and buf[3] and buf[4] == 0xe9):
        return va+9+int.from_bytes(buf[5:], 'little', signed=True)
    return None


def guard_prefix(buf, va):
    # lea guard(%rip), %rax; cmpb $0,(%rax); jne rel8/rel32
    if len(buf)<12 or buf[:3]!=b'\x48\x8d\x05' or buf[7:10]!=b'\x80\x38\x00':
        return None
    if buf[10]==0x75:
        end, start = 12,11
    elif len(buf)>=16 and buf[10:12]==b'\x0f\x85':
        end, start = 16,12
    else:
        return None
    return (va+7+int.from_bytes(buf[3:7],'little',signed=True),
            va+end+int.from_bytes(buf[start:end],'little',signed=True),end)


def guarded_counts(b, unknown, plt_end, offset, writable):
    guards = Counter()
    sites = slots = ret_sites = set_then_ret = 0
    for a,n in unknown.items():
        if a>=plt_end:
            continue
        p = offset(a,16,1)
        if p is None:
            continue
        result = guard_prefix(b[p:p+16],a)
        if result is None:
            continue
        flag, branch, size = result
        q = offset(flag,1,2)
        r = offset(branch,1,1)
        # BSS is initially zero even when the byte has no file offset.
        if (not writable(flag) or (q is not None and b[q]!=0) or not a+size<branch<=a+256
                or branch>=plt_end or r is None):
            continue
        guards[flag] += 1
        if b[r]==0xc3:
            ret_sites += 1
            for suffix in (b'\xc6\x00\x01', b'\x48\xc7\x00\x01\x00\x00\x00'):
                start = offset(branch-len(suffix),len(suffix)+1,1)
                if branch-len(suffix)>=a+size and start is not None and b[start:r]==suffix:
                    set_then_ret += 1
                    break
        sites += 1
        slots += n
    return dict(guard_prefix_targets=sites, guard_prefix_slots=slots,
                guard_branch_ret_targets=ret_sites, guard_set_then_ret_targets=set_then_ret,
                distinct_guard_bytes=len(guards), shared_guard_bytes=sum(n>1 for n in guards.values()))


def copy_plan(code, va, readonly, writable):
    """Return ordered (source RVA, destination RVA) pairs, or None.

    Caller bounds the input by the next known entry. Accept only full
    aligned RIP-relative AVX copy pairs followed by a near RET.
    """
    plan = []
    for pos in range(0, len(code), 16):
        if code[pos] == 0xc3:
            return tuple(plan) if plan else None
        if (len(code)-pos < 16 or code[pos:pos+4] != b'\xc5\xf8\x28\x05'
                or code[pos+8:pos+12] != b'\xc5\xf8\x29\x05'):
            return None
        src = va+pos+8+struct.unpack_from('<i',code,pos+4)[0]
        dst = va+pos+16+struct.unpack_from('<i',code,pos+12)[0]
        if (src|dst)&15 or not readonly(src,16) or not writable(dst,16):
            return None
        plan.append((src,dst))
    return None


def replay_copy_plan(data, data_rva, writes):
    """Apply pre-extracted 16-byte constants to a writable data-only buffer."""
    offsets = []
    for dst, raw in writes:
        off = dst-data_rva
        if dst&15 or len(raw)!=16 or off<0 or off>len(data)-16:
            raise ValueError('invalid constant write')
        offsets.append((off,bytes(raw)))
    for off, raw in offsets:
        data[off:off+16] = raw


def triage(b):
    inventory = audit(b)
    phoff = struct.unpack_from('<Q', b, 32)[0]
    count = struct.unpack_from('<H', b, 56)[0]
    loads, segments, rw = [], {}, []
    for i in range(count):
        t, f, o, v, _, n, mem, _ = struct.unpack_from('<II6Q', b, phoff+56*i)
        segments[t] = o, v, n
        if t == 1:
            if f&2: rw.append((v,v+mem))
            loads.append((v, v+n, o, f))

    def offset(va, size, flags=0):
        return next((o+va-lo for lo,hi,o,f in loads if lo<=va<=hi-size and f&flags==flags), None)

    do, _, ds = segments[2]
    tags = {}
    for i in range(do, do+ds-15, 16):
        k,v = struct.unpack_from('<QQ', b, i)
        if not k:
            break
        tags[k] = v
    base = segments[0x61000000][0]
    rel = {}
    occupied = set()
    for t,s in ((0x6100002f,0x61000031),(0x61000029,0x6100002d)):
        o,n = tags[t], tags[s]
        for slot,k,a in struct.iter_unpack('<QQq',b[base+o:base+o+n]):
            occupied.add(slot)
            if k==8:
                rel[slot] = a
    if len(rel) != inventory['relocation_types'].get(8,0):
        raise ValueError('inconsistent relative relocation inventory')
    eh, ev, _ = segments[0x6474e550]
    anchors = set()
    end = 0
    for i in range(inventory['unwind_entries']):
        loc, fde = struct.unpack_from('<ii',b,eh+12+8*i)
        start = ev+loc
        p = offset(ev+fde,16)
        if p is None:
            raise ValueError('FDE outside file-backed loads')
        enc_start, length = struct.unpack_from('<iI',b,p+8)
        if ev+fde+8+enc_start != start or not length or offset(start,length,1) is None:
            raise ValueError('invalid FDE code range')
        anchors.add(start)
        end = max(end,start+length)
    # Follow the donor scanner's PLT-boundary idea, but verify that every
    # RIP-relative stub addresses its corresponding JMPREL slot in order.
    o,n = tags[0x61000029], tags[0x6100002d]
    jmp = list(struct.iter_unpack('<QQq',b[base+o:base+o+n]))
    if not jmp or any(k&0xffffffff != 7 for _,k,_ in jmp):
        raise ValueError('expected nonempty x86-64 JUMP_SLOT table')
    boundaries = []
    span = 16*(len(jmp)+1)
    for va in range(end,end+0x10000):
        p = offset(va,span,1)
        if p is None or b[p:p+2]!=b'\xff\x35' or b[p+6:p+8]!=b'\xff\x25':
            continue
        for i,(slot,_,_) in enumerate(jmp,1):
            q = p+16*i
            if b[q:q+2]!=b'\xff\x25' or va+16*i+6+struct.unpack_from('<i',b,q+2)[0]!=slot:
                break
        else:
            boundaries.append(va+span)
    if len(boundaries)!=1:
        raise ValueError('could not verify unique PLT boundary')
    plt_end = boundaries[0]
    rx = {s:a for s,a in rel.items() if offset(a,1,1) is not None}
    unknown = Counter(a for a in rx.values() if a not in anchors)
    mixed, strong = Counter(), Counter()
    mixed_runs = null_header_runs = 0
    for run in runs(rx.items()):
        if len(run)<3 or not any(a in anchors for _,a in run):
            continue
        nonanchors = [a for _,a in run if a not in anchors]
        if not nonanchors:
            continue
        mixed_runs += 1
        mixed.update(nonanchors)
        s = run[0][0]
        p = offset(s-16,16)
        if p is not None and s-16 not in occupied and s-8 not in occupied:
            top, rtti = struct.unpack_from('<qQ',b,p)
            if -0x100000 <= top <= 0 and top%8==0 and rtti==0:
                null_header_runs += 1
                strong.update(nonanchors)
    entries = sorted(anchors | set(rx.values()) | {plt_end})
    plans = {}
    for a in unknown:
        if a>=plt_end:
            continue
        limit = min(entries[bisect_right(entries,a)], a+4096)
        p = offset(a,limit-a,1)
        if p is None:
            continue
        plan = copy_plan(b[p:p+limit-a],a,
            lambda x,n: x>=plt_end and offset(x,n,1) is not None,
            lambda x,n: any(lo<=x<=hi-n for lo,hi in rw))
        if plan:
            plans[a] = plan
    thunks = set()
    for a in unknown:
        p = offset(a,9,1)
        if p is not None and thunk_target(b[p:p+9],a) in anchors:
            thunks.add(a)
    return dict(**guarded_counts(b,unknown,plt_end,offset,lambda a: any(lo<=a<hi for lo,hi in rw)),
                rx_nonanchor_slots=sum(unknown.values()), rx_nonanchor_targets=len(unknown),
                verified_plt_stubs=len(jmp),
                copy_init_targets=len(plans),
                copy_init_writes=sum(map(len,plans.values())),
                copy_init_destinations=len({dst for p in plans.values() for _,dst in p}),
                pre_plt_end_nonanchor_slots=sum(n for a,n in unknown.items() if a<plt_end),
                pre_plt_end_nonanchor_targets=sum(a<plt_end for a in unknown),
                post_plt_nonanchor_slots=sum(n for a,n in unknown.items() if a>=plt_end),
                post_plt_nonanchor_targets=sum(a>=plt_end for a in unknown),
                mixed_runs=mixed_runs, mixed_slots=sum(mixed.values()), mixed_targets=len(mixed),
                null_header_runs=null_header_runs, null_header_slots=sum(strong.values()),
                null_header_targets=len(strong), strict_adjustor_targets=len(thunks),
                strict_adjustor_slots=sum(unknown[a] for a in thunks))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf', type=Path)
    try:
        print(json.dumps(triage(p.parse_args().elf.read_bytes()),sort_keys=True))
    except (OSError, ValueError, struct.error) as e:
        p.exit(2,f'{e}\n')
