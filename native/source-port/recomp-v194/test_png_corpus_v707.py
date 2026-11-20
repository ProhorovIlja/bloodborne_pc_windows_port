# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare native raw rows with Go image/png using its local test corpus."""
import argparse
import ctypes as c
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory

GO = '''package main
import("image/png";"image/color";"os";"bufio")
func main(){
    f,e:=os.Open(os.Args[1]); if e!=nil { panic(e) }; defer f.Close()
    m,e:=png.Decode(f); if e!=nil { panic(e) }
    b:=m.Bounds(); out:=bufio.NewWriter(os.Stdout)
    for y:=b.Min.Y;y<b.Max.Y;y++ { for x:=b.Min.X;x<b.Max.X;x++ {
        p:=color.NRGBAModel.Convert(m.At(x,y)).(color.NRGBA)
        out.Write([]byte{p.R,p.G,p.B,p.A})
    } }; if e:=out.Flush();e!=nil { panic(e) }
}
'''


def run(compilers):
    goroot = Path(subprocess.check_output(['go','env','GOROOT'],text=True).strip())
    corpus = goroot/'src/image/png/testdata'
    paths = sorted(corpus.glob('*.png')) + sorted((corpus/'pngsuite').glob('*.png'))
    flags = subprocess.check_output(['pkg-config','--cflags','--libs','libpng'],text=True).split()
    with TemporaryDirectory(prefix='bb707-') as d:
        root = Path(d)
        (root/'main.go').write_text(GO)
        subprocess.run(['go','build','-o',root/'oracle',root/'main.go'],check=True)
        cases = []
        for path in paths:
            data = path.read_bytes()
            w,h,depth,mode,_,_,interlace = struct.unpack_from('>IIBBBBB',data,16)
            bad = path.name.startswith('invalid-')
            if bad or depth!=8 or mode not in (2,6) or interlace:
                cases.append((data,3 if mode==2 else 4,0,0,None,bad))
                continue
            rgba = subprocess.check_output([root/'oracle',path],timeout=10)
            if len(rgba)!=w*h*4:
                raise ValueError(f'bad oracle output: {path.name}')
            channels = 3 if mode==2 else 4
            rgb = b''.join(rgba[i:i+3] for i in range(0,len(rgba),4)) if channels==3 else rgba
            cases.append((data,channels,w,h,rgb,False))
        if not cases or not any(x[4] for x in cases) or not any(x[5] for x in cases):
            raise ValueError('Go source/test corpus is required')
        for index,cc in enumerate(compilers):
            so = root/f'decoder{index}.so'
            subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                            Path(__file__).with_name('png_rows_v706.c'),*flags,'-o',so],check=True)
            step = c.CDLL(str(so)).bb_png_rows706
            P,N,U = c.c_void_p,c.c_size_t,c.c_uint32
            step.argtypes = P,N,P,N,N,c.c_uint,U,c.POINTER(U),c.POINTER(U)
            exact = rejected = malformed = pixels = 0
            for data,ch,w,h,expected,bad in cases:
                row = w*ch
                stride = row+11 if expected is not None else 8192*4
                size = (h-1)*stride+row if expected is not None else 8*1024*1024
                fill = b'\xa5'*size
                dst = c.create_string_buffer(fill,size)
                a,b = U(17),U(19)
                status = step(data,len(data),dst,size,stride,ch,8192,c.byref(a),c.byref(b))
                if expected is None:
                    assert not status and dst.raw==fill and (a.value,b.value)==(17,19)
                    rejected += 1
                    malformed += bad
                else:
                    assert status and (a.value,b.value)==(w,h)
                    assert dst.raw==(b'\xa5'*11).join(expected[i:i+row] for i in range(0,len(expected),row))
                    exact += 1
                    pixels += w*h
            print(f'{cc}: {exact} exact files ({pixels} pixels); '
                  f'{rejected} unchanged refusals ({malformed} malformed fixtures)')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cc',action='append',default=[])
    run(p.parse_args().cc or ['cc'])
