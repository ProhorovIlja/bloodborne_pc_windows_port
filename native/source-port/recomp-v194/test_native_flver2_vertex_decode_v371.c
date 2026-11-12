/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic-only FLVER2 vertex semantic, offset, normalization regression.
 */
#include "native_flver2_vertex_decode_v371.h"
#include "native_flver2_geometry_v362.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define TEST_BYTES_V371 0x294u
#define DATA_V371 0x200u
static void w16(unsigned char *p,unsigned off,uint16_t v) {
    p[off]=(unsigned char)v;p[off+1]=(unsigned char)(v>>8);
}
static void w32(unsigned char *p,unsigned off,uint32_t v) {
    w16(p,off,(uint16_t)v);w16(p,off+2,(uint16_t)(v>>16));
}
static void wf32(unsigned char *p,unsigned off,float f) {
    uint32_t bits=0;memcpy(&bits,&f,4);w32(p,off,bits);
}
static void build(unsigned char *p) {
    memset(p,0,TEST_BYTES_V371);
    memcpy(p,"FLVER\0L\0",8);
    w32(p,8,0x20014);w32(p,12,DATA_V371);w32(p,16,148);
    w32(p,24,1);w32(p,32,1);w32(p,36,1);
    p[0x49]=1;
    w32(p,0x50,1);w32(p,0x54,1);
    p[0xa0]=1;w32(p,0xa0+16,UINT32_MAX);
    w32(p,0xa0+32,1);w32(p,0xa0+36,0x1c0);
    w32(p,0xa0+40,1);w32(p,0xa0+44,0x1c4);
    w32(p,0xd0+8,3);w32(p,0xd0+16,6);w32(p,0xd0+24,16);
    w32(p,0xf0+8,44);w32(p,0xf0+12,3);
    w32(p,0xf0+24,132);w32(p,0xf0+28,16);
    w32(p,0x110,8);w32(p,0x110+12,0x120);
    const uint32_t sem[]={0,3,6,6,2,1,10,5};
    const uint32_t types[]={2,0x11,0x11,0x11,0x11,0x13,0x13,0x16};
    const uint32_t idx[]={0,0,0,1,0,0,1,0};
    const uint32_t offsets[]={0,12,16,20,24,28,32,36};
    for(unsigned i=0;i<8;++i) {
        unsigned m=0x120+i*20;
        w32(p,m+4,offsets[i]);w32(p,m+8,types[i]);
        w32(p,m+12,sem[i]);w32(p,m+16,idx[i]);
    }
    w16(p,DATA_V371,0);w16(p,DATA_V371+2,1);w16(p,DATA_V371+4,2);
    for(unsigned i=0;i<3;++i) {
        unsigned o=DATA_V371+16+i*44;
        wf32(p,o+0,-0.75f+(float)i*0.75f);
        wf32(p,o+4,0.25f+(float)i*0.25f);
        wf32(p,o+8,1.5f);
        p[o+12]=127;p[o+13]=127;p[o+14]=254;p[o+15]=6;
        p[o+16]=254;p[o+17]=127;p[o+18]=127;p[o+19]=127;
        p[o+20]=127;p[o+21]=254;p[o+22]=127;p[o+23]=127;
        p[o+24]=0;p[o+25]=1;p[o+26]=2;p[o+27]=3;
        p[o+28]=128;p[o+29]=64;p[o+30]=32;p[o+31]=31;
        p[o+32]=255;p[o+33]=128;p[o+34]=0;p[o+35]=255;
        w16(p,o+36,2048);w16(p,o+38,(uint16_t)-1024);
        w16(p,o+40,4096);w16(p,o+42,512);
    }
}
static void accepted(unsigned char *p) {
    ShytNativeFlver2GeometryV362 g={0};
    assert(shyt_native_flver2_geometry_probe_v362(p,TEST_BYTES_V371,&g));
    assert(g.total_vertices==3 && g.validated_vertex_bytes==132);
    ShytNativeFlver2VertexLayoutV371 layout={0};
    assert(shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371,0,&layout));
    assert(layout.vertex_count==3 && layout.stride==44 && layout.member_count==8);
    assert(layout.present==0x1ffu && layout.data_offset==DATA_V371+16);
    ShytNativeFlver2VertexV371 vertices[3]={0};
    assert(shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,
                                                   0,0,3,vertices,3));
    for(unsigned i=0;i<3;++i) {
        const ShytNativeFlver2VertexV371 *v=&vertices[i];
        assert(fabsf(v->position[0]-(-0.75f+(float)i*0.75f))<1e-5f);
        assert(v->normal[0]==0 && v->normal[1]==0 && v->normal[2]==1);
        assert(v->normal_w==6);
        assert(v->tangents[0][0]==1.f && v->tangents[1][1]==1.f);
        assert(v->bone_indices[1]==1 && v->bone_indices[3]==3);
        assert(fabsf(v->bone_weights[0]-128.0f/255.0f)<1e-6f);
        assert(v->color[0]==1.f && v->color[2]==0.f);
        assert(fabsf(v->color[1]-128.0f/255.0f)<1e-6f);
        assert(v->uv[0][0]==1.f && v->uv[0][1]==-0.5f);
        assert(v->uv[1][0]==2.f && v->uv[1][1]==0.25f);
        assert(v->present==0x1ffu);
    }
    ShytNativeFlver2VertexV371 one={0};
    assert(shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,0,
                                                   1,1,&one,1));
    assert(one.position[0]==0.f);
}
static void alternate_layouts(unsigned char *p) {
    /* 36-byte unskinned LOD layout is also present in both real FLVER
     * headers, although the selected original large models use 44-byte VBs. */
    build(p);
    unsigned char original[132];
    memcpy(original,p+DATA_V371+16,sizeof(original));
    for(unsigned i=0;i<3;++i) {
        const unsigned char *old=original+i*44;
        unsigned char *new_data=p+DATA_V371+16+i*36;
        memcpy(new_data,old,24);
        memcpy(new_data+24,old+32,4); /* RGBA color */
        memcpy(new_data+28,old+36,8); /* two signed UV pairs */
    }
    w32(p,16,124);w32(p,0xf0+8,36);w32(p,0xf0+24,108);
    w32(p,0x110,6);
    w32(p,0x120+4*20+4,24);
    w32(p,0x120+4*20+8,0x13);
    w32(p,0x120+4*20+12,10);
    w32(p,0x120+4*20+16,1);
    w32(p,0x120+5*20+4,28);
    w32(p,0x120+5*20+8,0x16);
    w32(p,0x120+5*20+12,5);
    w32(p,0x120+5*20+16,0);
    ShytNativeFlver2VertexLayoutV371 layout={0};
    assert(shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371,0,&layout));
    assert(layout.vertex_count==3 && layout.stride==36 &&
           layout.present==(0x1ffu & ~(SHYT_V371_BONE_INDICES | SHYT_V371_BONE_WEIGHTS)));
    ShytNativeFlver2VertexV371 data[3]={0};
    assert(shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,0,0,3,data,3));
    assert(data[2].uv[0][0]==1.0f && data[2].uv[1][1]==0.25f);
    assert(data[2].bone_weights[0]==0 && data[2].bone_indices[1]==0);
    /* Position-only rendering is the exact explicitly supported V370 GPU
     * input layout; no packed normal/UV semantics may be invented. */
    build(p);
    memcpy(original,p+DATA_V371+16,sizeof(original));
    for(unsigned i=0;i<3;++i)
        memcpy(p+DATA_V371+16+i*12,original+i*44,12);
    w32(p,16,52);w32(p,0xf0+8,12);w32(p,0xf0+24,36);
    w32(p,0x110,1);
    memset(data,0,sizeof(data));
    assert(shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371,0,&layout));
    assert(layout.stride==12 && layout.member_count==1 &&
           layout.present==SHYT_V371_POSITION);
    assert(shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,0,0,3,data,3));
    assert(data[0].position[0]==-0.75f && data[2].position[0]==0.75f);
    assert(data[0].color[0]==1.0f && data[0].normal[0]==0.0f);
    build(p);
}
static void rejected(unsigned char *p) {
    ShytNativeFlver2VertexLayoutV371 layout={0};
    assert(!shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371,0,&layout));
    assert(layout.vertex_count==0 && layout.present==0);
}
int main(void) {
    unsigned char p[TEST_BYTES_V371];
    build(p);accepted(p);
    ShytNativeFlver2VertexLayoutV371 layout={0};
    assert(!shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371,1,&layout));
    assert(!shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371-1,0,&layout));
    assert(!shyt_native_flver2_vertex_layout_v371(NULL,0,0,&layout));
    assert(!shyt_native_flver2_vertex_layout_v371(p,TEST_BYTES_V371,0,
        (ShytNativeFlver2VertexLayoutV371 *)(void *)(p+16)));
    ShytNativeFlver2VertexV371 one={0};
    assert(!shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,
                                                    0,3,1,&one,1));
    assert(!shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,
                                                    0,0,1,&one,0));
    assert(!shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,
                                                    0,0,4,&one,1));
    assert(!shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,
         0,0,1,(ShytNativeFlver2VertexV371 *)(void *)(p+DATA_V371+16),1));
    /* V362 accepts layout type 0x10 with same width; V371 refuses unsupported
     * normal semantics instead of interpreting unknown packing as Byte4B. */
    w32(p,0x120+20+8,0x10);rejected(p);build(p);
    w32(p,0x120+20*2+12,3);rejected(p);build(p); /* duplicate normal */
    w32(p,0x120+20*3+16,0);rejected(p);build(p); /* duplicate tangent */
    w32(p,0x120+20*5+16,3);rejected(p);build(p); /* bad weights index */
    w32(p,0x120+20*7+12,6);rejected(p);build(p); /* UVPair tangent */
    w32(p,0x120+20*0+4,4);rejected(p);build(p); /* offset tampering */
    w32(p,0xf0+8,40);rejected(p);build(p); /* incorrect stride */
    /* Nonfinite positions must not produce partial output. */
    w32(p,DATA_V371+16+44+0,0x7fc00000u);
    ShytNativeFlver2VertexV371 two[2];memset(two,0xA5,sizeof(two));
    assert(!shyt_native_flver2_decode_vertices_v371(p,TEST_BYTES_V371,0,0,2,two,2));
    unsigned char hold[sizeof(two)];memset(hold,0xA5,sizeof(hold));
    assert(memcmp(two,hold,sizeof(two))==0);
    build(p);accepted(p);
    alternate_layouts(p);
    puts("NATIVE_V371_SYNTHETIC_REAL_LAYOUT_FLOAT3_PACKED_VERTEX_DECODE_PASS");
    return 0;
}
