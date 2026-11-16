# SPDX-License-Identifier: GPL-2.0-or-later
import ctypes as c
import sys
from prepare_data_v474 import prepare


class Patch(c.Structure):
    _fields_ = [('offset', c.c_size_t), ('value', c.c_uint64)]


def load(path):
    fn = c.CDLL(path).bb_data_init_v474
    fn.argtypes = [c.c_void_p,c.c_size_t,c.c_void_p,c.c_size_t,c.POINTER(Patch),c.c_size_t]
    fn.restype = c.c_int
    return fn


def test(path):
    image = bytes(range(128))
    loads = [(1,5,0,0,0,32,32,16),(1,6,32,256,0,32,80,16)]
    tls = (7,4,48,272,0,8,16,8)
    layout = prepare(image,loads,tls,[256,296])
    assert layout.template == bytes(8)+image[40:64]
    assert (layout.tls_template,layout.tls_size,layout.tls_align) == (image[48:56],16,8)
    for bad in ([255],[256,260],[272],[335]):
        try:
            prepare(image,loads,tls,bad)
        except ValueError:
            pass
        else:
            raise AssertionError('bad slot accepted')
    fn = load(path)
    dst = (c.c_ubyte*82)(*([165]*82))
    out = c.byref(dst,1)
    valid = (Patch*2)(Patch(0,0x102030405060708), Patch(40,99))
    original = bytes(dst)
    for patches in ((Patch*2)(Patch(0,5),Patch(7,6)),
                    (Patch*1)(Patch(73,7)), (Patch*1)(Patch(8,9))):
        assert not fn(out,80,layout.template,32,patches,len(patches))
        assert bytes(dst) == original
    assert fn(out,80,layout.template,32,valid,2)
    expected = bytearray(layout.template+bytes(48))
    for patch in valid:
        expected[patch.offset:patch.offset+8] = patch.value.to_bytes(8,'little')
    assert bytes(dst) == b'\xa5'+expected+b'\xa5'
    # A separate fresh TLS block per host context; no pointer/TCB semantics here.
    tls_a, tls_b = (c.c_ubyte*16)(), (c.c_ubyte*16)()
    for block in (tls_a,tls_b):
        assert fn(block,16,layout.tls_template,8,None,0)
        assert bytes(block)==image[48:56]+bytes(8)
    tls_a[0] ^= 255
    assert bytes(tls_b)==image[48:56]+bytes(8)
    print('V474_DATA_TEMPLATE_PASS')


if __name__ == '__main__':
    test(sys.argv[1])
