/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V374. Independent, allocation-free FLVER2 topology walker.
 * Public SoulsFormats FaceSet documentation used as a layout reference;
 * no external implementation copied. No game resources contained here.
 */
#include "native_flver2_mesh_topology_v374.h"
#include "native_flver2_geometry_v362.h"
#include <stdint.h>
#include <string.h>
#define V374_MOTION 0x80000000u
#define V374_LOD1 0x01000000u
#define V374_LOD2 0x02000000u
#define V374_KNOWN (V374_MOTION|V374_LOD1|V374_LOD2)

static uint32_t le32_v374(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
           ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint32_t index_v374(const unsigned char *p, uint64_t offset,
                           uint32_t element_bytes) {
    if (element_bytes==2u)
        return (uint32_t)p[offset]|((uint32_t)p[offset+1u]<<8);
    return le32_v374(p+offset);
}
static int range_v374(uint64_t offset,uint64_t bytes,uint64_t limit) {
    return offset<=limit && bytes<=limit-offset;
}
static int overlap_v374(const void *a,size_t an,const void *b,size_t bn) {
    if (!an||!bn) return 0;
    if (!a||!b) return 1;
    const uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
    if (an>UINTPTR_MAX-av||bn>UINTPTR_MAX-bv) return 1;
    return av<bv+bn && bv<av+an;
}
/* Exactly one triangle enumeration, used for both counting and output.
 * The first pass MUST validate the entire input before output is modified.
 */
static int enumerate_v374(const unsigned char *p,
    const ShytNativeMeshFaceV374 *f,uint32_t *destination,
    uint32_t *triangle_count,uint32_t *degenerate_count,
    uint32_t *restart_count) {
    uint32_t triangles=0,degenerates=0,restarts=0;
    uint32_t first=0,second=0,valid=0,parity=0;
    const uint32_t sentinel=f->index_element_bytes==2u?0xFFFFu:UINT32_MAX;
    if (!f->triangle_strip && f->index_count%3u!=0u) return 0;
    if (f->triangle_strip && f->vertex_count>=sentinel) return 0;
    for(uint32_t i=0;i<f->index_count;++i) {
        const uint32_t v=index_v374(p,(uint64_t)f->index_absolute_offset+
                                        (uint64_t)i*f->index_element_bytes,
                                        f->index_element_bytes);
        if (v==sentinel) {
            if (!f->triangle_strip) return 0;
            ++restarts;
            valid=0;parity=0;
            continue;
        }
        if(v>=f->vertex_count) return 0;
        if(!f->triangle_strip) {
            if(valid==0) {first=v;valid=1;continue;}
            if(valid==1) {second=v;valid=2;continue;}
            valid=0;
            if(first==second || second==v || first==v) {++degenerates;continue;}
            if(destination) {
                destination[3u*triangles]=first;
                destination[3u*triangles+1u]=second;
                destination[3u*triangles+2u]=v;
            }
            ++triangles;
            continue;
        }
        if(valid==0) {first=v;valid=1;continue;}
        if(valid==1) {second=v;valid=2;continue;}
        const uint32_t a=first,b=second;
        first=second;second=v;
        if(a==b||b==v||a==v) {++degenerates;}
        else {
            if(destination) {
                destination[3u*triangles]=(parity&1u)?b:a;
                destination[3u*triangles+1u]=(parity&1u)?a:b;
                destination[3u*triangles+2u]=v;
            }
            ++triangles;
        }
        parity^=1u; /* degenerates flip strip winding too */
    }
    *triangle_count=triangles;
    *degenerate_count=degenerates;
    *restart_count=restarts;
    return 1;
}
static int info_v374(const unsigned char *p,size_t bytes,uint32_t mesh,
                      uint32_t face_slot,ShytNativeMeshFaceV374 *out) {
    ShytNativeFlver2GeometryV362 g={0};
    if (!shyt_native_flver2_geometry_probe_v362(p,bytes,&g) ||
        mesh>=g.mesh_count) return 0;
    const uint64_t mr=(uint64_t)g.first_mesh_record_offset+48u*mesh;
    if (!range_v374(mr,48u,bytes)) return 0;
    const uint32_t face_count=le32_v374(p+mr+32);
    const uint32_t face_refs=le32_v374(p+mr+36);
    const uint32_t vb_count=le32_v374(p+mr+40);
    const uint32_t vb_refs=le32_v374(p+mr+44);
    if (face_slot>=face_count || vb_count==0u || vb_count>3u ||
        !range_v374(face_refs,4u*(uint64_t)face_count,g.data_offset) ||
        !range_v374(vb_refs,4u*(uint64_t)vb_count,g.data_offset)) return 0;
    const uint32_t face=le32_v374(p+(uint64_t)face_refs+4u*face_slot);
    if (face>=g.face_set_count) return 0;
    const uint64_t fr=(uint64_t)g.first_face_record_offset+32u*face;
    if (!range_v374(fr,32u,bytes)) return 0;
    const uint32_t flags=le32_v374(p+fr);
    const uint32_t raw_lod=flags&(V374_LOD1|V374_LOD2);
    if ((flags&~V374_KNOWN)!=0u || raw_lod==(V374_LOD1|V374_LOD2))
        return 0; /* Unknown higher LOD or EDGE compression */
    const uint32_t idx_count=le32_v374(p+fr+8);
    const uint32_t rel_offset=le32_v374(p+fr+12);
    const uint32_t stored=le32_v374(p+fr+16);
    const uint32_t index_bits=le32_v374(p+fr+24);
    if ((index_bits!=16u && index_bits!=32u) ||
        (uint64_t)idx_count*(index_bits/8u)!=stored ||
        !range_v374(rel_offset,stored,g.data_bytes)) return 0;
    const uint64_t absolute=(uint64_t)g.data_offset+rel_offset;
    if (absolute>UINT32_MAX || !range_v374(absolute,stored,bytes)) return 0;
    ShytNativeMeshFaceV374 tmp={0};
    tmp.mesh_index=mesh;
    tmp.face_set_index=face;
    tmp.face_slot=face_slot;
    tmp.material_index=le32_v374(p+mr+4);
    tmp.default_bone_index=(int32_t)le32_v374(p+mr+16);
    tmp.local_bone_count=le32_v374(p+mr+20);
    tmp.vertex_buffer_count=vb_count;
    tmp.lod=raw_lod==V374_LOD1 ? SHYT_V374_LOD1 :
            raw_lod==V374_LOD2 ? SHYT_V374_LOD2 : SHYT_V374_LOD_BASE;
    tmp.motion_blur=(flags&V374_MOTION)!=0u;
    tmp.triangle_strip=p[fr+4]!=0u;
    tmp.cull_backfaces=p[fr+5]!=0u;
    tmp.index_element_bytes=index_bits/8u;
    tmp.index_count=idx_count;
    tmp.index_absolute_offset=(uint32_t)absolute;
    uint32_t expected_vertices=UINT32_MAX;
    for (uint32_t i=0;i<vb_count;++i) {
        uint32_t vb=le32_v374(p+(uint64_t)vb_refs+4u*i);
        if(vb>=g.vertex_buffer_count) return 0;
        const uint64_t vr=(uint64_t)g.first_vertex_record_offset+32u*vb;
        if (!range_v374(vr,32u,bytes)) return 0;
        uint32_t n=le32_v374(p+vr+12);
        if(expected_vertices!=UINT32_MAX && expected_vertices!=n) return 0;
        tmp.vertex_buffer_indices[i]=vb;
        expected_vertices=n;
    }
    tmp.vertex_count=expected_vertices;
    if(!enumerate_v374(p,&tmp,NULL,&tmp.triangle_count,
                       &tmp.degenerate_count,&tmp.restart_count)) return 0;
    *out=tmp;
    return 1;
}
int shyt_native_flver2_mesh_face_v374(const void *flver,size_t bytes,
    uint32_t mesh,uint32_t face_slot,ShytNativeMeshFaceV374 *out) {
    if (!out) return 0;
    if (flver && overlap_v374(flver,bytes,out,sizeof(*out))) return 0;
    memset(out,0,sizeof(*out));
    if(!flver||bytes<128) return 0;
    ShytNativeMeshFaceV374 tmp={0};
    if(!info_v374((const unsigned char*)flver,bytes,mesh,face_slot,&tmp))
        return 0;
    *out=tmp;
    return 1;
}
int shyt_native_flver2_triangles_v374(const void *flver,size_t bytes,
    uint32_t mesh,uint32_t face_slot,uint32_t *triangles,
    size_t capacity,ShytNativeMeshFaceV374 *info) {
    if(!info) return 0;
    if (flver && overlap_v374(flver,bytes,info,sizeof(*info))) return 0;
    if (triangles && (capacity>SIZE_MAX/sizeof(uint32_t) ||
         overlap_v374(triangles,capacity*sizeof(uint32_t),info,sizeof(*info)) ||
         (flver && overlap_v374(flver,bytes,triangles,
                                 capacity*sizeof(uint32_t))))) return 0;
    memset(info,0,sizeof(*info));
    if(!flver||bytes<128 || (!triangles && capacity)) return 0;
    ShytNativeMeshFaceV374 tmp={0};
    if(!info_v374((const unsigned char*)flver,bytes,mesh,face_slot,&tmp))
        return 0;
    if (triangles) {
        const size_t needed=(size_t)tmp.triangle_count*3u;
        if(needed>capacity) return 0;
        uint32_t emitted=0,deg=0,res=0;
        if(!enumerate_v374((const unsigned char*)flver,&tmp,triangles,
                            &emitted,&deg,&res) || emitted!=tmp.triangle_count ||
           deg!=tmp.degenerate_count || res!=tmp.restart_count) return 0;
    }
    *info=tmp;
    return 1;
}
