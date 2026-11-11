/* SPDX-License-Identifier: GPL-2.0-or-later
 * Narrow native Bloodborne / Dark Souls III FLVER2 metadata validator.
 * Independently authored in C after comparing publicly documented
 * SoulsFormats FLVER2 record semantics. No game data distributed.
 */
#include "native_flver2_geometry_v362.h"
#include <stdint.h>
#include <string.h>

#define FLVER_HEADER_V362 0x80ull
#define FLVER_MAX_BYTES_V362 (512ull*1024ull*1024ull)
#define FLVER_MAX_RECORDS_V362 1000000u

static uint32_t le32_v362(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
           ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint16_t le16_v362(const unsigned char *p) {
    return (uint16_t)((unsigned)p[0]|((unsigned)p[1]<<8));
}
static int within_v362(uint64_t p,uint64_t size,uint64_t limit) {
    return p<=limit && size<=limit-p;
}
static int subarray_v362(uint64_t offset,uint64_t count,uint64_t stride,
                         uint64_t end) {
    return stride && count<=end/stride && within_v362(offset,count*stride,end);
}
static uint32_t type_bytes_v362(uint32_t type) {
    switch(type) {
    case 0x01: return 8;  /* Float2 */
    case 0x02: return 12; /* Float3 */
    case 0x03: return 16; /* Float4 */
    case 0x10: case 0x11: case 0x12: case 0x13:
    case 0x15: case 0x2f: return 4;
    case 0x16: case 0x18: case 0x1a: case 0x2e:
        return 8;
    default: return 0; /* EDGE or unverified packing mode */
    }
}
static int check_face_v362(const unsigned char *p,uint64_t face,
                           uint64_t data_offset,uint64_t data_size,
                           uint64_t total_size,uint64_t *bytes,uint32_t *indices) {
    const uint32_t flags=le32_v362(p+face);
    const uint32_t count=le32_v362(p+face+8);
    const uint32_t offset=le32_v362(p+face+12);
    const uint32_t stored=le32_v362(p+face+16);
    const uint32_t width=le32_v362(p+face+24);
    if ((flags&0x40000000u)!=0 || /* unsupported EDGE compressed indices */
        (width!=16u && width!=32u) ||
        p[face+4]>1u || p[face+5]>1u ||
        le32_v362(p+face+20)!=0u || le32_v362(p+face+28)!=0u ||
        count>FLVER_MAX_RECORDS_V362 ||
        (uint64_t)count*(width/8u)!=(uint64_t)stored ||
        !within_v362(offset,stored,data_size) ||
        !within_v362(data_offset+offset,stored,total_size)) return 0;
    *bytes=(uint64_t)stored;
    *indices=count;
    return 1;
}
static int check_vertex_v362(const unsigned char *p,uint64_t rec,
    uint32_t layouts,uint64_t data_offset,uint64_t data_size,uint64_t total_size,
    uint32_t *vertex_count, uint64_t *buffer_bytes) {
    const uint32_t index=le32_v362(p+rec);
    const uint32_t layout=le32_v362(p+rec+4);
    const uint32_t stride=le32_v362(p+rec+8);
    const uint32_t count=le32_v362(p+rec+12);
    const uint32_t bytes=le32_v362(p+rec+24);
    const uint32_t offset=le32_v362(p+rec+28);
    if ((index&~0x60000003u)!=0u || layout>=layouts ||
        !stride || stride>1024u || count>FLVER_MAX_RECORDS_V362 ||
        le32_v362(p+rec+16)!=0u || le32_v362(p+rec+20)!=0u ||
        (uint64_t)stride*count!=(uint64_t)bytes ||
        !within_v362(offset,bytes,data_size) ||
        !within_v362(data_offset+offset,bytes,total_size)) return 0;
    *vertex_count=count;
    *buffer_bytes=bytes;
    return 1;
}
int shyt_native_flver2_geometry_probe_v362(
    const void *flver,size_t file_size,ShytNativeFlver2GeometryV362 *out) {
    if(!out) return 0;
    memset(out,0,sizeof(*out));
    if(!flver || file_size<FLVER_HEADER_V362 || file_size>FLVER_MAX_BYTES_V362)
        return 0;
    const unsigned char *p=(const unsigned char *)flver;
    if(memcmp(p,"FLVER\0L\0",8)!=0) return 0; /* Win64 little-endian only */
    const uint32_t version=le32_v362(p+8);
    const uint32_t data_offset=le32_v362(p+12);
    const uint32_t data_size=le32_v362(p+16);
    if((version!=0x20013u && version!=0x20014u) ||
       data_offset<FLVER_HEADER_V362 || data_offset>file_size ||
       !within_v362(data_offset,data_size,file_size) ||
       p[0x49]!=1u || p[0x4B]!=0u ||
       p[0x4A]>1u || p[0x5E]!=0u || p[0x5F]!=0u ||
       le32_v362(p+0x60)!=0u || le32_v362(p+0x64)!=0u ||
       le32_v362(p+0x6c)!=0u || le32_v362(p+0x70)!=0u ||
       le32_v362(p+0x74)!=0u || le32_v362(p+0x78)!=0u ||
       le32_v362(p+0x7c)!=0u) return 0;
    const uint32_t dummies=le32_v362(p+20);
    const uint32_t materials=le32_v362(p+24);
    const uint32_t bones=le32_v362(p+28);
    const uint32_t meshes=le32_v362(p+32);
    const uint32_t vertices=le32_v362(p+36);
    const uint32_t faces=le32_v362(p+0x50);
    const uint32_t layouts=le32_v362(p+0x54);
    const uint32_t textures=le32_v362(p+0x58);
    const uint32_t counts[]={dummies,materials,bones,meshes,faces,vertices,layouts,textures};
    const uint32_t strides[]={64,32,128,48,32,32,16,32};
    uint64_t starts[8],pos=FLVER_HEADER_V362;
    for(unsigned i=0;i<8;++i) {
        if(counts[i]>FLVER_MAX_RECORDS_V362 ||
           !subarray_v362(pos,counts[i],strides[i],data_offset)) return 0;
        starts[i]=pos;
        pos+=(uint64_t)counts[i]*strides[i];
    }
    const uint32_t header_index_bits=p[0x48];
    if(header_index_bits!=0 && header_index_bits!=16 && header_index_bits!=32)
        return 0;
    uint64_t verified_indices=0,verified_index_bytes=0,verified_vertex_bytes=0;
    uint32_t vertex_total=0;
    for(uint32_t i=0;i<faces;++i) {
        uint64_t bytes=0;
        uint32_t count=0;
        uint64_t rec=starts[4]+(uint64_t)i*32u;
        if(!check_face_v362(p,rec,data_offset,data_size,file_size,&bytes,&count))
            return 0;
        verified_indices+=count;
        verified_index_bytes+=bytes;
    }
    for(uint32_t i=0;i<layouts;++i) {
        uint64_t rec=starts[6]+(uint64_t)i*16;
        uint32_t members=le32_v362(p+rec);
        uint32_t offset=le32_v362(p+rec+12);
        if(!members || members>64u ||
           le32_v362(p+rec+4) || le32_v362(p+rec+8) ||
           !subarray_v362(offset,members,20u,data_offset)) return 0;
        uint32_t stride=0;
        for(uint32_t k=0;k<members;++k) {
            uint64_t member=(uint64_t)offset+(uint64_t)k*20;
            uint32_t type=le32_v362(p+member+8);
            uint32_t width=type_bytes_v362(type);
            if(!width || le32_v362(p+member+4)!=stride ||
               stride>1024u-width) return 0;
            stride+=width;
        }
        if(stride==0) return 0;
    }
    for(uint32_t i=0;i<vertices;++i) {
        uint64_t rec=starts[5]+(uint64_t)i*32;
        uint32_t count=0;
        uint64_t bytes=0;
        if(!check_vertex_v362(p,rec,layouts,data_offset,data_size,
                               file_size,&count,&bytes)) return 0;
        /* Confirm the packed vertex buffer agrees with the layout. */
        uint32_t layout=le32_v362(p+rec+4);
        uint64_t layout_rec=starts[6]+(uint64_t)layout*16;
        uint32_t members=le32_v362(p+layout_rec);
        uint32_t offset=le32_v362(p+layout_rec+12);
        uint32_t layout_size=0;
        for(uint32_t j=0;j<members;++j)
            layout_size+=type_bytes_v362(le32_v362(p+offset+(uint64_t)j*20+8));
        if(layout_size!=le32_v362(p+rec+8)) return 0;
        if(vertex_total>UINT32_MAX-count) return 0;
        vertex_total+=count;
        verified_vertex_bytes+=bytes;
    }
    for(uint32_t i=0;i<meshes;++i) {
        uint64_t rec=starts[3]+(uint64_t)i*48;
        int32_t material=(int32_t)le32_v362(p+rec+4);
        int32_t default_bone=(int32_t)le32_v362(p+rec+16);
        uint32_t bone_count=le32_v362(p+rec+20);
        uint32_t bounds_off=le32_v362(p+rec+24);
        uint32_t bones_off=le32_v362(p+rec+28);
        uint32_t face_count=le32_v362(p+rec+32);
        uint32_t faces_off=le32_v362(p+rec+36);
        uint32_t vb_count=le32_v362(p+rec+40);
        uint32_t vb_off=le32_v362(p+rec+44);
        if(p[rec]>1u || p[rec+1] || p[rec+2] || p[rec+3] ||
            material<0 || (uint32_t)material>=materials ||
            le32_v362(p+rec+8) || le32_v362(p+rec+12) ||
            (default_bone!=-1 && (default_bone<0 || (uint32_t)default_bone>=bones)) ||
            (bounds_off && !within_v362(bounds_off,24u,data_offset)) ||
            (bone_count && !subarray_v362(bones_off,bone_count,4u,data_offset)) ||
            !face_count || face_count>faces ||
            !subarray_v362(faces_off,face_count,4u,data_offset) ||
            !vb_count || vb_count>3u ||
            !subarray_v362(vb_off,vb_count,4u,data_offset)) return 0;
        for(uint32_t j=0;j<bone_count;++j) {
            uint32_t idx=le32_v362(p+(uint64_t)bones_off+(uint64_t)j*4);
            if(idx>=bones) return 0;
        }
        uint32_t mesh_vertex_count=UINT32_MAX;
        for(uint32_t j=0;j<vb_count;++j) {
            uint32_t index=le32_v362(p+(uint64_t)vb_off+(uint64_t)j*4);
            if(index>=vertices) return 0;
            uint64_t vrec=starts[5]+(uint64_t)index*32u;
            uint32_t n=le32_v362(p+vrec+12);
            if(mesh_vertex_count!=UINT32_MAX && mesh_vertex_count!=n) return 0;
            mesh_vertex_count=n;
        }
        for(uint32_t j=0;j<face_count;++j) {
            uint32_t index=le32_v362(p+(uint64_t)faces_off+(uint64_t)j*4);
            if(index>=faces) return 0;
            uint64_t frec=starts[4]+(uint64_t)index*32u;
            uint32_t index_count=le32_v362(p+frec+8);
            uint32_t offset=le32_v362(p+frec+12);
            uint32_t width=le32_v362(p+frec+24);
            uint64_t ip=data_offset+(uint64_t)offset;
            /* The index spans are checked by check_face_v362. Inspect
             * referenced indices before future GPU upload. */
            for(uint32_t k=0;k<index_count;++k) {
                uint32_t value=width==16 ? le16_v362(p+ip+(uint64_t)k*2) :
                                           le32_v362(p+ip+(uint64_t)k*4);
                if(value>=mesh_vertex_count &&
                   !(width==16 && value==0xFFFFu) &&
                   !(width==32 && value==0xFFFFFFFFu)) return 0;
            }
        }
    }
    out->version=version;
    out->data_offset=data_offset;
    out->data_bytes=data_size;
    out->dummy_count=dummies;
    out->material_count=materials;
    out->bone_count=bones;
    out->mesh_count=meshes;
    out->vertex_buffer_count=vertices;
    out->face_set_count=faces;
    out->layout_count=layouts;
    out->texture_count=textures;
    out->total_vertices=vertex_total;
    out->total_index_elements=verified_indices;
    out->validated_vertex_bytes=verified_vertex_bytes;
    out->validated_index_bytes=verified_index_bytes;
    out->first_mesh_record_offset=(uint32_t)starts[3];
    out->first_face_record_offset=(uint32_t)starts[4];
    out->first_vertex_record_offset=(uint32_t)starts[5];
    return 1;
}
