# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline LLVM direct-flow inventory; no native generation or guest execution."""
from collections import Counter, deque
import ctypes as c
import struct


def llvm(path):
    lib = c.CDLL(path)
    for name in ('TargetInfo','TargetMC','Disassembler'):
        getattr(lib,'LLVMInitializeX86'+name)()
    make=lib.LLVMCreateDisasm
    make.argtypes=[c.c_char_p,c.c_void_p,c.c_int,c.c_void_p,c.c_void_p]
    make.restype=c.c_void_p
    ctx=make(b'x86_64-pc-linux',None,0,None,None)
    if not ctx:
        raise ValueError('LLVM x86 backend missing')
    step=lib.LLVMDisasmInstruction
    step.argtypes=[c.c_void_p,c.c_char_p,c.c_uint64,c.c_uint64,c.c_char_p,c.c_size_t]
    step.restype=c.c_size_t
    close=lib.LLVMDisasmDispose
    close.argtypes=[c.c_void_p]
    close.restype=None
    buf=c.create_string_buffer(256)
    def decode(raw,addr):
        n=step(ctx,raw,len(raw),addr,buf,256)
        if not n:
            return 0,b''
        return n,next((w for w in buf.value.split() if w not in PREFIX_NAMES),b'')
    return decode,lambda:close(ctx)


PREFIX_NAMES=set(b'rep repe repne repz repnz lock bnd notrack data16 addr32'.split())
PREFIX=set(bytes.fromhex('26 2e 36 3e 64 65 66 67 f2 f3')+bytes(range(0x40,0x50)))
CALL=set(b'call callq callw calll lcall lcallq lcallw lcalll'.split())
JUMP=set(b'jmp jmpq jmpw jmpl ljmp ljmpq ljmpw ljmpl'.split())
STOP=set(b'ret retq retw retl lret lretq lretw lretl retf retfq retfw retfl iret iretq iretw iretl int int1 int3 into ud0 ud1 ud2 ud2b hlt xabort sysret sysretq sysretl sysexit sysexitq rsm'.split())
SYSTEM={b'syscall',b'sysenter'}


def edge(raw,m):
    i=0
    while i<len(raw) and raw[i] in PREFIX:
        i+=1
    b=raw[i:]
    if not b:
        return 'unknown',None
    op=b[0]
    if m in CALL and op==0xe8 and len(b)==5:
        return 'call',struct.unpack_from('<i',b,1)[0]
    if m in JUMP and op==0xe9 and len(b)==5:
        return 'jump',struct.unpack_from('<i',b,1)[0]
    if m in JUMP and op==0xeb and len(b)==2:
        return 'jump',struct.unpack_from('<b',b,1)[0]
    if m in CALL|JUMP and op==0xff and len(b)>=2:
        reg=b[1]>>3&7
        if m in CALL and reg==2:
            return 'indirect_call',None
        if m in JUMP and reg==4:
            return 'indirect_jump',None
    if m.startswith((b'j',b'loop')) and m not in JUMP:
        if len(b)==2 and (0x70<=op<=0x7f or 0xe0<=op<=0xe3):
            return 'conditional',struct.unpack_from('<b',b,1)[0]
        if len(b)==6 and op==0x0f and 0x80<=b[1]<=0x8f:
            return 'conditional',struct.unpack_from('<i',b,2)[0]
    if m==b'xbegin' and len(b)==6 and b[:2]==b'\xc7\xf8':
        return 'conditional',struct.unpack_from('<i',b,2)[0]
    return 'unknown',None


def walk(image,off,base,size,roots,pointers,decode):
    if not 0<size<=128<<20 or not 0<=off<=len(image)-size or not 0<=base<=2**64-size:
        raise ValueError('invalid RX extent')
    if not roots or any(not base<=a<base+size for a in roots):
        raise ValueError('invalid seed set')
    # 0 untouched, 1 instruction start, 2 interior, 3 failed decode.
    marks=bytearray(size)
    queue=deque(sorted(a-base for a in roots))
    targets=set()
    n=Counter(dict.fromkeys('instructions bytes failed overlap call jump conditional indirect_call indirect_jump out_of_rx unknown system'.split(),0))
    while queue:
        p=queue.popleft()
        while p<size:
            if marks[p]:
                if marks[p]==2:
                    n['overlap']+=1
                break
            raw=image[off+p:off+min(p+15,size)]
            width,m=decode(raw,base+p)
            if not 0<width<=len(raw) or not m:
                marks[p]=3
                n['failed']+=1
                break
            if any(marks[p+1:p+width]):
                n['overlap']+=1
                break
            marks[p]=1
            marks[p+1:p+width]=b'\x02'*(width-1)
            n['instructions']+=1
            n['bytes']+=width
            nxt=p+width
            if m in STOP:
                break
            if m in SYSTEM:
                n['system']+=1
                break
            if m.startswith((b'j',b'ljmp',b'call',b'lcall',b'loop',b'xbegin',b'ret',b'iret',b'lret')):
                kind,disp=edge(raw[:width],m)
                n[kind]+=1
                if disp is not None:
                    target=nxt+disp
                    if 0<=target<size:
                        queue.append(target)
                        if kind=='call':
                            targets.add(base+target)
                    else:
                        n['out_of_rx']+=1
                if kind in ('jump','indirect_jump','unknown'):
                    break
            p=nxt
    observed=lambda a:base<=a<base+size and marks[a-base]==1
    return dict(n,seed_ids=len(roots),decoded_seeds=sum(map(observed,roots)),
                direct_call_targets=len(targets),decoded_new_call_targets=sum(map(observed,targets-roots)),
                relocation_targets=len(pointers),relocation_targets_at_decoded_starts=sum(map(observed,pointers)),
                native_generation_run=False,runtime_execution_run=False)
