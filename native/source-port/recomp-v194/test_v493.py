# SPDX-License-Identifier: GPL-2.0-or-later
from test_v492 import p
from index_v493 import write_index,emit_index
from io import StringIO
import re

alu=p/'alu.c'
alu.write_text(re.sub(r'\bf([0-9]+)\b',r'alu_f\1',alu.read_text(encoding='ascii')),encoding='ascii')
(p/'index_v493.inc').unlink(missing_ok=True)
assert write_index(p)==14
for args in (([1],[2],{1:2},[3],[4]),([1],[2],{5:9},[3],[4])):
    try:
        emit_index(*args,StringIO())
    except (ValueError,KeyError):
        pass
    else:
        raise AssertionError('invalid route index accepted')
