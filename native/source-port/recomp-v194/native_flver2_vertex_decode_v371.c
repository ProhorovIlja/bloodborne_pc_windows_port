/* SPDX-License-Identifier: GPL-2.0-or-later
 * FLVER2 canonical vertex extraction, safe bounds and supported members.
 * Format facts verified against private BB/DS3 owner assets and public
 * SoulsFormats metadata; no third-party source copied.
 */
#include "native_flver2_vertex_decode_v371.h"
#include "native_flver2_geometry_v362.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

static uint32_t le32_v371(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 |
        (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int16_t le_s16_v371(const unsigned char *p) {
    uint16_t u=(uint16_t)((unsigned)p[0] | (unsigned)p[1]<<8);
    /* Avoid implementation-defined uint16 -> int16 conversion. */
    return (int16_t)(u<=INT16_MAX ? (int32_t)u : ((int32_t)u-65536));
}
static int range_v371(uint64_t start,uint64_t count,uint64_t size) {
    return start<=size && count<=size-start;
}
static int overlap_v371(const void *a,size_t n,const void *b,size_t m) {
    if(!n || !m) return 0;
    if(!a || !b) return 1;
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(n>UINTPTR_MAX-aa || m>UINTPTR_MAX-bb) return 1;
    return aa<bb+m && bb<aa+n;
}
static float float_v371(const unsigned char *p) {
    uint32_t bits=le32_v371(p);
    float f=0;
    memcpy(&f,&bits,sizeof(f));
    return f;
}
static int supported_v371(uint32_t type,uint32_t semantic,uint32_t idx,
                          uint32_t *mask) {
    if(semantic==0 && idx==0 && type==2) {*mask=SHYT_V371_POSITION;return 1;}
    if(semantic==3 && idx==0 && type==0x11) {*mask=SHYT_V371_NORMAL;return 1;}
    if(semantic==6 && idx<=1 && type==0x11) {
        *mask=idx==0?SHYT_V371_TANGENT0:SHYT_V371_TANGENT1;return 1;
    }
    if(semantic==2 && idx==0 && type==0x11) {*mask=SHYT_V371_BONE_INDICES;return 1;}
    if(semantic==1 && idx==0 && type==0x13) {*mask=SHYT_V371_BONE_WEIGHTS;return 1;}
    if(semantic==10 && idx<=1 && type==0x13) {*mask=SHYT_V371_COLOR;return 1;}
    if(semantic==5 && idx==0 && type==0x16) {
        *mask=SHYT_V371_UV0|SHYT_V371_UV1;return 1;
    }
    return 0;
}
int shyt_native_flver2_vertex_layout_v371(
    const void *flver,size_t file_bytes,uint32_t buffer_index,
    ShytNativeFlver2VertexLayoutV371 *out) {
    if(!out) return 0;
    if(flver && overlap_v371(out,sizeof(*out),flver,file_bytes)) return 0;
    memset(out,0,sizeof(*out));
    ShytNativeFlver2GeometryV362 g={0};
    if(!flver || !shyt_native_flver2_geometry_probe_v362(flver,file_bytes,&g) ||
       buffer_index>=g.vertex_buffer_count || g.layout_count>1000000u ||
       sizeof(float)!=4) return 0;
    const unsigned char *p=(const unsigned char *)flver;
    const uint64_t vb_rec=(uint64_t)g.first_vertex_record_offset+32ull*buffer_index;
    const uint32_t lidx=le32_v371(p+vb_rec+4);
    if(lidx>=g.layout_count) return 0;
    /* V362 stores first vertex record, but layout records follow VBs. */
    const uint64_t layout_records=(uint64_t)g.first_vertex_record_offset+
                                  (uint64_t)g.vertex_buffer_count*32u;
    const uint64_t layout_rec=layout_records+(uint64_t)lidx*16u;
    if(!range_v371(layout_rec,16,g.data_offset))return 0;
    const uint32_t members=le32_v371(p+layout_rec);
    const uint32_t members_offset=le32_v371(p+layout_rec+12);
    const uint32_t stride=le32_v371(p+vb_rec+8);
    const uint32_t count=le32_v371(p+vb_rec+12);
    const uint64_t data_offset=(uint64_t)g.data_offset+le32_v371(p+vb_rec+28);
    if(!members || members>SHYT_V371_MAX_MEMBERS ||
       !range_v371(members_offset,(uint64_t)members*20u,g.data_offset) ||
       !range_v371(data_offset,(uint64_t)stride*count,file_bytes) ||
       data_offset>UINT32_MAX) return 0;
    ShytNativeFlver2VertexLayoutV371 layout={0};
    layout.buffer_index=buffer_index;
    layout.vertex_count=count;
    layout.stride=stride;
    layout.data_offset=(uint32_t)data_offset;
    layout.member_count=members;
    uint32_t seen=0,offset=0;
    for(uint32_t i=0;i<members;++i) {
        const uint64_t member=(uint64_t)members_offset+(uint64_t)i*20u;
        const uint32_t type=le32_v371(p+member+8);
        const uint32_t semantic=le32_v371(p+member+12);
        const uint32_t index=le32_v371(p+member+16);
        uint32_t size=0,mask=0;
        switch(type){case 2:size=12;break;
            case 0x11:case 0x13:size=4;break;
            case 0x16:size=8;break;
            default:return 0;
        }
        if(!supported_v371(type,semantic,index,&mask) ||
           (seen&mask) || le32_v371(p+member+4)!=offset ||
           offset>stride || size>stride-offset) return 0;
        layout.members[i]=(ShytNativeFlver2VertexMemberV371){
            semantic,type,index,offset,size};
        seen|=mask;offset+=size;
    }
    if(offset!=stride || !(seen&SHYT_V371_POSITION))return 0;
    /* Bone weights without corresponding indices and vice versa would be
     * ambiguous for skinning and must not be represented as complete data. */
    if (!!(seen&SHYT_V371_BONE_WEIGHTS)!=
        !!(seen&SHYT_V371_BONE_INDICES))return 0;
    layout.present=seen;
    *out=layout;
    return 1;
}
static int decode_one_v371(const unsigned char *p,
    const ShytNativeFlver2VertexLayoutV371 *layout,uint32_t vertex,
    ShytNativeFlver2VertexV371 *out) {
    ShytNativeFlver2VertexV371 value={0};
    const unsigned char *rec=p+layout->data_offset+(size_t)vertex*layout->stride;
    value.present=layout->present;
    value.color[0]=value.color[1]=value.color[2]=value.color[3]=1.0f;
    for(uint32_t i=0;i<layout->member_count;++i){
        const ShytNativeFlver2VertexMemberV371 *m=&layout->members[i];
        const unsigned char *v=rec+m->offset;
        switch(m->semantic){
        case 0:
            for(uint32_t k=0;k<3;++k){
                float f=float_v371(v+k*4);
                if(!isfinite(f))return 0;
                value.position[k]=f;
            }
            break;
        case 3:
            for(uint32_t k=0;k<3;++k)value.normal[k]=((float)v[k]-127.0f)/127.0f;
            value.normal_w=v[3];
            break;
        case 6:
            for(uint32_t k=0;k<4;++k)
                value.tangents[m->semantic_index][k]=((float)v[k]-127.0f)/127.0f;
            break;
        case 2:
            for(uint32_t k=0;k<4;++k)value.bone_indices[k]=v[k];
            break;
        case 1:
            for(uint32_t k=0;k<4;++k)value.bone_weights[k]=(float)v[k]/255.0f;
            break;
        case 10:
            for(uint32_t k=0;k<4;++k)value.color[k]=(float)v[k]/255.0f;
            break;
        case 5:
            for(uint32_t k=0;k<2;++k)
                for(uint32_t t=0;t<2;++t)
                    value.uv[k][t]=(float)le_s16_v371(v+k*4+t*2)/2048.0f;
            break;
        default: return 0;
        }
    }
    *out=value;
    return 1;
}
int shyt_native_flver2_decode_vertices_v371(
    const void *flver,size_t file_bytes,uint32_t buffer_index,
    uint32_t first_vertex,uint32_t count,
    ShytNativeFlver2VertexV371 *output,size_t capacity) {
    if (count && !output) return 0;
#if SIZE_MAX <= UINT32_MAX
    if ((size_t)count>SIZE_MAX/sizeof(*output)) return 0;
#endif
    if (count>capacity ||
        (flver && overlap_v371(flver,file_bytes,output,
                              (size_t)count*sizeof(*output))))return 0;
    ShytNativeFlver2VertexLayoutV371 layout;
    if(!shyt_native_flver2_vertex_layout_v371(flver,file_bytes,buffer_index,&layout) ||
       first_vertex>layout.vertex_count || count>layout.vertex_count-first_vertex)
        return 0;
    const unsigned char *p=(const unsigned char *)flver;
    /* Preflight all floats to avoid partially writing output after a
     * malformed NaN/Inf late in the range. No secondary allocations. */
    for(uint32_t i=0;i<count;++i){
        ShytNativeFlver2VertexV371 scratch;
        if(!decode_one_v371(p,&layout,first_vertex+i,&scratch))return 0;
    }
    for(uint32_t i=0;i<count;++i)
        if(!decode_one_v371(p,&layout,first_vertex+i,&output[i]))return 0;
    return 1;
}
