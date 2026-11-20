# SPDX-License-Identifier: GPL-2.0-or-later
from startup_ro_v476 import prepare

image = bytes(range(64))
source = 100, 16, 32
assert prepare(image,source,[(100,3),(101,5),(109,1),(100,3)],[],[]) == (
    [(100,0,6),(109,6,1)],image[16:22]+image[25:26])
for requests, code, reloc in [([(107,2)], [(102,110),(104,105)], []),
                             ([(107,2)], [], [100]), ([(131,2)], [], []),
                             ([(100,0)], [], []), ([], [], [])]:
    try:
        prepare(image,source,requests,code,reloc)
    except ValueError:
        continue
    raise AssertionError('accepted invalid spans')
