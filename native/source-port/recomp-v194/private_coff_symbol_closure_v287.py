#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V287: private original-game AMD64 COFF external-symbol link closure.

Run ONLY after V275 has SHA-verified every object from the owner's
original-game AOT generated-C set. Inspects actual native COFF symbol
tables, never guest executable code, and NEVER prints/stores original
retail identifiers. An unresolved COFF name is not proof of game failure:
Windows CRT, DLL imports and platform shims must be resolved by the
future legitimate Windows PE link step.
"""
from __future__ import annotations
import mmap
from pathlib import Path
import struct

import compile_private_win64_coff_v217 as coff

MAX_OBJECTS=512
MAX_TOTAL_SYMBOLS=5_000_000
MAX_NAME_LENGTH=1024
EXTERNAL=2
WEAK_EXTERNAL=105

def _name(image:mmap.mmap, name8:bytes, strings_at:int,
          strings_size:int)->bytes:
    if name8[:4]!=b'\0'*4:
        name=name8.split(b'\0',1)[0]
        if not name: raise ValueError('unnamed external COFF symbol')
        return name
    offset=struct.unpack_from('<I',name8,4)[0]
    if not 4<=offset<strings_size:
        raise ValueError('invalid COFF long symbol offset')
    at=strings_at+offset
    end=min(strings_at+strings_size,at+MAX_NAME_LENGTH+1)
    last=image.find(b'\0',at,end)
    if last<0 or last==at or last-at>MAX_NAME_LENGTH:
        raise ValueError('unbounded COFF symbol string')
    return bytes(image[at:last])

def symbols_in_object(path:Path)->tuple[set[bytes],set[bytes],int,int]:
    if not coff.coff_ok(path):
        raise ValueError('untrusted/truncated private AMD64 COFF')
    with path.open('rb') as stream:
        with mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as image:
            _,_,_,offset,count,_,_=struct.unpack_from('<HHLLLHH',image,0)
            if count>MAX_TOTAL_SYMBOLS:
                raise ValueError('unbounded COFF symbols')
            strings_at=offset+count*18
            string_size=struct.unpack_from('<I',image,strings_at)[0]
            definitions:set[bytes]=set()
            missing:set[bytes]=set()
            weak=0
            i=0
            while i<count:
                at=offset+i*18
                raw=image[at:at+18]
                if len(raw)!=18:raise ValueError('truncated COFF symbol entry')
                name8,value,section,_,storage,aux=struct.unpack(
                    '<8sLhHBB',raw)
                if i+aux>=count and aux:
                    raise ValueError('COFF auxiliary symbol count out of bounds')
                if storage in (EXTERNAL,WEAK_EXTERNAL):
                    name=_name(image,name8,strings_at,string_size)
                    if storage==WEAK_EXTERNAL:
                        weak+=1
                    elif section>0 or section==-1 or (section==0 and value>0):
                        definitions.add(name)
                    elif section==0 and value==0:
                        missing.add(name)
                i+=1+aux
            return definitions,missing,count,weak

def verify_external_symbol_closure(object_files:list[Path])->dict:
    if not 1<=len(object_files)<=MAX_OBJECTS:
        raise ValueError('unsafe private object count')
    defined:set[bytes]=set()
    undefined:set[bytes]=set()
    total_symbols=weak=duplicate_definitions=0
    for object_file in object_files:
        defs,needs,count,w=symbols_in_object(object_file)
        total_symbols+=count
        if total_symbols>MAX_TOTAL_SYMBOLS:
            raise ValueError('original-game symbol budget exceeded')
        duplicate_definitions+=len(defined.intersection(defs))
        defined.update(defs)
        undefined.update(needs)
        weak+=w
    unresolved=undefined.difference(defined)
    # Aggregate counts ONLY, no names, imports, private addresses or hashes.
    return {
        'verified_amd64_coff_objects':len(object_files),
        'external_definitions':len(defined),
        'external_references':len(undefined),
        'external_references_unresolved_in_game_objects':len(unresolved),
        'duplicate_external_names_across_objects':duplicate_definitions,
        'weak_external_symbols':weak,
        'coff_symbols_inspected':total_symbols,
        'windows_crt_import_resolution_done':False,
        'native_pe_link_complete':False,
        'guest_runtime_removed':False,
    }
