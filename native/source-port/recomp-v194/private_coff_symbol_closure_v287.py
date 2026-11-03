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
    # V290: a bounded object dependency graph highlights strongly
    # connected native recomp modules that must be linked together.
    # Full original symbol bytes remain private and never leave memory.
    all_objects:list[tuple[set[bytes],set[bytes]]]=[]
    symbol_owners:dict[bytes,set[int]]={}
    for object_id,object_file in enumerate(object_files):
        defs,needs,count,w=symbols_in_object(object_file)
        total_symbols+=count
        if total_symbols>MAX_TOTAL_SYMBOLS:
            raise ValueError('original-game symbol budget exceeded')
        duplicate_definitions+=len(defined.intersection(defs))
        for name in defs:
            symbol_owners.setdefault(name,set()).add(object_id)
        all_objects.append((defs,needs))
        defined.update(defs)
        undefined.update(needs)
        weak+=w
    unresolved=undefined.difference(defined)
    # V328: private *aggregate* host-import demand. An unresolved
    # external may be referenced by hundreds of original COFF modules:
    # raw counts alone conceal how broadly a missing Windows subsystem
    # blocks linking. Keep every symbol name in memory only, never print
    # or serialize raw private import names or per-module paths.
    unresolved_by_object=[len(needs.intersection(unresolved))
                          for _,needs in all_objects]
    unresolved_sites=sum(unresolved_by_object)
    blocked_objects=sum(bool(n) for n in unresolved_by_object)
    max_per_object=max(unresolved_by_object)
    # V328: count only unresolved reference sites in linear time.
    # Avoid O(unique imports * every original module) on 9k+ shards.
    unresolved_users={name:0 for name in unresolved}
    for _,needs in all_objects:
        for name in needs.intersection(unresolved):
            unresolved_users[name]+=1
    single_owner_unresolved=sum(count==1
                                for count in unresolved_users.values())
    dependencies:list[set[int]]=[set() for _ in object_files]
    for object_id,(_,needs) in enumerate(all_objects):
        for name in needs:
            for owner in symbol_owners.get(name,()):
                if owner!=object_id:
                    dependencies[object_id].add(owner)
    # Tarjan SCC, bounded by MAX_OBJECTS=512, well under default
    # Python recursion depth. A cycle means these objects cannot be
    # independently analyzed as link-ready modules.
    serial=0
    indices=[-1]*len(object_files)
    lows=[0]*len(object_files)
    on_stack=[False]*len(object_files)
    stack:list[int]=[]
    component_sizes:list[int]=[]
    def visit(node:int)->None:
        nonlocal serial
        indices[node]=lows[node]=serial
        serial+=1
        stack.append(node)
        on_stack[node]=True
        for nxt in dependencies[node]:
            if indices[nxt]==-1:
                visit(nxt)
                lows[node]=min(lows[node],lows[nxt])
            elif on_stack[nxt]:
                lows[node]=min(lows[node],indices[nxt])
        if lows[node]==indices[node]:
            count=0
            while True:
                last=stack.pop()
                on_stack[last]=False
                count+=1
                if last==node:break
            component_sizes.append(count)
    for node in range(len(object_files)):
        if indices[node]==-1:visit(node)
    # Aggregate counts ONLY, no names, imports, private addresses or hashes.
    return {
        'verified_amd64_coff_objects':len(object_files),
        'external_definitions':len(defined),
        'external_references':len(undefined),
        'external_references_unresolved_in_game_objects':len(unresolved),
        'unresolved_reference_sites_across_objects':unresolved_sites,
        'object_modules_blocked_by_host_imports':blocked_objects,
        'object_modules_self_contained_against_external_imports':
            len(object_files)-blocked_objects,
        'max_unresolved_imports_in_one_object':max_per_object,
        'unresolved_symbols_needed_by_exactly_one_object':
            single_owner_unresolved,
        'duplicate_external_names_across_objects':duplicate_definitions,
        'weak_external_symbols':weak,
        'coff_symbols_inspected':total_symbols,
        'direct_object_dependency_edges':sum(map(len,dependencies)),
        'strongly_connected_object_components':len(component_sizes),
        'cyclic_object_components':sum(n>1 for n in component_sizes),
        'largest_cyclic_or_single_component':max(component_sizes),
        'windows_crt_import_resolution_done':False,
        'native_pe_link_complete':False,
        'guest_runtime_removed':False,
    }
