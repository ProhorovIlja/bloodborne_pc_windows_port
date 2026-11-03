#!/usr/bin/env python3
"""V206: audit real original game PS4 platform import families, privately.

Uses an owner-provided decrypted executable, strictly at BUILD TIME.
No game code, NIDs, offsets, raw addresses, personal data or assets emitted:
only category totals and *public SDK library* names. Not proof of a working
Windows implementation. No original-game bytes enter GitHub CI.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import struct

MAX_BYTES=512*1024*1024
ALPHABET='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-'
CRT={'libc','libkernel','libScePosix','libSceRtc'}
GPU={'libSceGnmDriver','libSceVideoOut','libSceScreenShot'}
AUDIO={'libSceAudioOut','libSceAudioIn','libSceAjm','libSceVoice','libSceAvPlayer'}
IO={'libSceSaveData','libSceSaveDataDialog','libSceFios2','libScePlayGo','libSceAppContent'}
INPUT={'libScePad','libSceMouse','libSceImeDialog'}
NETWORK={'libSceNet','libSceNetCtl','libSceHttp','libSceSsl'}

def family(library:str)->str:
    if library in CRT:return 'win32_crt_kernel_time'
    if library in GPU:return 'windows_gpu_present'
    if library in AUDIO:return 'windows_audio_video_voice'
    if library in IO:return 'windows_asset_io_save_data'
    if library in INPUT:return 'windows_input_ime'
    if library in NETWORK:return 'windows_network_http_tls'
    if library.startswith('libSceNp'):return 'account_multiplayer_social'
    if library.startswith('libSce'):return 'other_platform_services'
    return 'unknown'

def name_key(value:int)->str:
    out=ALPHABET[value&63]
    value>>=6
    while value:
        out=ALPHABET[value&63]+out
        value>>=6
    return out

def inspect(path:Path)->dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError('decrypted private PS4 executable file missing/unsafe')
    if not 1_000_000<=path.stat().st_size<=MAX_BYTES:
        raise ValueError('unreasonable original executable size')
    data=path.read_bytes()
    if data[:7]!=b'\x7fELF\x02\x01\x01':
        raise ValueError('decrypted little-endian ELF64 required')
    elf_type,machine=struct.unpack_from('<HH',data,16)
    if (elf_type,machine)!=(0xfe10,62):
        raise ValueError('original PS4 x86-64 ELF required')
    phoff=struct.unpack_from('<Q',data,32)[0]
    phsize,phcount=struct.unpack_from('<HH',data,54)
    if phsize!=56 or not 1<=phcount<=256 or phoff+phsize*phcount>len(data):
        raise ValueError('bad private ELF program headers')
    segments=[struct.unpack_from('<IIQQQQQQ',data,phoff+phsize*i) for i in range(phcount)]
    def segment(kind):
        result=[x for x in segments if x[0]==kind]
        if len(result)!=1:raise ValueError('missing original ELF dynamic segment')
        s=result[0]
        if s[2]+s[5]>len(data):raise ValueError('bad segment length')
        return s
    dyn=segment(2);ld=segment(0x61000000)
    tags=[]
    if dyn[5]%16:raise ValueError('bad dynamic record size')
    for pos in range(dyn[2],dyn[2]+dyn[5],16):
        tag,val=struct.unpack_from('<QQ',data,pos)
        if tag==0:break
        tags.append((tag,val))
    tagmap=dict(tags)
    def block(offset,length):
        if offset<0 or length<0 or offset+length>ld[5]:
            raise ValueError('bad original linker metadata bounds')
        return memoryview(data)[ld[2]+offset:ld[2]+offset+length]
    st=bytes(block(tagmap[0x61000035],tagmap[0x61000037]))
    def public_string(offset):
        if offset<0 or offset>=len(st):raise ValueError('invalid name index')
        z=st.find(b'\0',offset)
        if z<0 or z-offset>512:raise ValueError('invalid string')
        return st[offset:z].decode('ascii')
    libs={};mods={}
    for tag,value in tags:
        if tag not in (0x61000013,0x61000015,0x6100000d,0x6100000f):continue
        k=name_key(value>>48)
        target=libs if tag in (0x61000013,0x61000015) else mods
        value_name=public_string(value&0xffffffff)
        if k in target and target[k]!=value_name:
            raise ValueError('conflicting PS4 import library IDs')
        target[k]=value_name
    syms=block(tagmap[0x61000039],tagmap[0x6100003f])
    if len(syms)%24:raise ValueError('malformed PS4 dynamic symbols')
    symbol_count=len(syms)//24
    frequencies=collections.Counter();types=collections.Counter();unresolved=0;imports=0
    for a,b in ((0x61000029,0x6100002d),(0x6100002f,0x61000031)):
        reloc=block(tagmap[a],tagmap[b])
        if len(reloc)%24:raise ValueError('malformed relocation table')
        for at in range(0,len(reloc),24):
            address,info,addend=struct.unpack_from('<QQq',reloc,at)
            kind=info&0xffffffff
            if kind not in (6,7):continue
            sym_id=info>>32
            if sym_id>=symbol_count:raise ValueError('out-of-range import symbol')
            name_offset,meta,other,section,va,sz=struct.unpack_from(
                '<IBBHQQ',syms,sym_id*24)
            if section!=0:raise ValueError('import relocation has local symbol')
            name=public_string(name_offset)
            triple=name.split('#')
            if len(triple)!=3:unresolved+=1;continue
            lib=libs.get(triple[1]);mod=mods.get(triple[2])
            if not lib or not mod:unresolved+=1;continue
            frequencies[lib]+=1;types[kind]+=1;imports+=1
    buckets=collections.Counter()
    for lib,n in frequencies.items():buckets[family(lib)]+=n
    return {'format':'shyt-private-original-import-family-v206',
            'original_ps4_dynamic_library_ids':len(libs),
            'original_ps4_dynamic_module_ids':len(mods),
            'original_dynamic_symbol_count':symbol_count,
            'reconciled_import_relocation_slots':imports,
            'unresolved_import_relocation_slots':unresolved,
            'jump_slot_count':types[7],
            'global_data_slot_count':types[6],
            'library_families':dict(sorted(buckets.items())),
            'highest_volume_sdk_libraries':dict(frequencies.most_common(12)),
            'all_windows_native_imports_implemented':False,
            'game_boot_proven':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--decrypted-elf',type=Path,required=True)
    a=p.parse_args()
    result=inspect(a.decrypted_elf)
    print('SHYT_V206_PRIVATE_ORIGINAL_IMPORT_FAMILY_AUDIT_PASS')
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=='__main__':main()
