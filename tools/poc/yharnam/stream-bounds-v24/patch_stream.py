#!/usr/bin/env python3
"""V24 fail-closed source fix for unbounded co-op stream reassembly."""
from pathlib import Path
PATH='server/coop/coop_stream.h'
HEADER='server/coop/sh_message_bounds.hpp'
HERE=Path(__file__).resolve().parent
def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise ValueError(f'V24 {label}: expected 1 anchor, found {n}')
    return s.replace(old,new,1)
def transform(s):
    if 'SH-STREAM-BOUNDS-V24' in s:
        raise ValueError('V24 already applied')
    s=one(s,'#include "coop/game_link.h"',
      '#include "coop/game_link.h"\n#include "coop/sh_message_bounds.hpp" // SH-STREAM-BOUNDS-V24',
      'header include')
    s=one(s,'            partial.clear();\n            restarted = true;',
      '            partial.Reset();\n            restarted = true;',
      'peer restart reset')
    s=one(s,'''            partial.insert(partial.end(), chunk.begin() + 1, chunk.end());
            if ((chunk[0] & LastChunk) != 0) {
                messages.push_back(std::exchange(partial, {}));
            }''',
      '''            // A peer can send non-final fragments forever. Bound its RAM.
            std::vector<u8> completed;
            if (partial.Push(
                    std::span<const u8>(chunk.data()+1, chunk.size()-1),
                    (chunk[0] & LastChunk) != 0, completed)) {
                messages.push_back(std::move(completed));
            }''',
      'bounded reassembly')
    s=one(s,'    std::vector<u8> partial;',
      '    SeamlessHunt::StreamBounds::Assembler partial;',
      'bounded partial member')
    return s
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.source.resolve()==a.output.resolve():p.error('no in-place source rewrite')
    a.output.write_text(transform(a.source.read_text('utf-8')),encoding='utf-8')
