#!/usr/bin/env python3
"""V219 private COFF cache input hashing; never print source paths/bytes."""
from __future__ import annotations
import hashlib
from pathlib import Path
import tempfile

MAX_FILES=20000
MAX_TOTAL_BYTES=512*1024**2
MAX_FILE_BYTES=64*1024**2
HEADER_SUFFIXES={'.h','.hpp','.inc','.inl','.hh','.hxx'}

def sha(path:Path)->str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>256*1024**2:
        raise ValueError('unsafe compiler dependency')
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()

def input_fingerprint(upstream:Path,sdk:Path,compiler:str)->dict[str,str]:
    roots=[(upstream/'src',True),(upstream/'deps/include',False),
           (sdk/'include',False)]
    h=hashlib.sha256()
    count=total=0
    for i,(root,headers_only) in enumerate(roots):
        if root.is_symlink() or not root.is_dir():
            raise ValueError('missing/unsafe include root')
        for path in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
            if path.is_symlink():
                raise ValueError('include symlink can escape vetted roots')
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError('nonregular compiler input')
            if headers_only and path.suffix.lower() not in HEADER_SUFFIXES:
                continue
            size=path.stat().st_size
            count+=1
            total+=size
            if size>MAX_FILE_BYTES or count>MAX_FILES or total>MAX_TOTAL_BYTES:
                raise ValueError('compiler header tree exceeds safety limits')
            name=f'{i}:{path.relative_to(root).as_posix()}'.encode('utf-8')
            h.update(len(name).to_bytes(4,'little'))
            h.update(name)
            h.update(size.to_bytes(8,'little'))
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1048576),b''):
                    h.update(chunk)
    return {'include_tree_sha256':h.hexdigest(),
            'compiler_binary_sha256':sha(Path(compiler).resolve(strict=True))}

def selftest()->None:
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)/'upstream'
        sdk=Path(temp)/'sdk'
        for path in (root/'src',root/'deps/include',sdk/'include'):
            path.mkdir(parents=True)
        (root/'src/recomp.h').write_text('#define X 1\n')
        (root/'deps/include/zydis.h').write_text('a')
        (sdk/'include/stdlib.h').write_text('b')
        compiler=Path(temp)/'compiler'
        compiler.write_bytes(b'fake')
        a=input_fingerprint(root,sdk,str(compiler))
        (sdk/'include/stdlib.h').write_text('changed')
        b=input_fingerprint(root,sdk,str(compiler))
        assert a['include_tree_sha256']!=b['include_tree_sha256']
        compiler.write_bytes(b'changed')
        c=input_fingerprint(root,sdk,str(compiler))
        assert b['compiler_binary_sha256']!=c['compiler_binary_sha256']
        (root/'src/recomp.h').write_text('#define X 2\n')
        d=input_fingerprint(root,sdk,str(compiler))
        assert d['include_tree_sha256']!=c['include_tree_sha256']
        (sdk/'include/escape.h').symlink_to(compiler)
        try:
            input_fingerprint(root,sdk,str(compiler))
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe symlink accepted')
    print('SHYT_V219_COFF_HEADER_AND_COMPILER_HASH_TEST_PASS')

if __name__=='__main__':
    selftest()
