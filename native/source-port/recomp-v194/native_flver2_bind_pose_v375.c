/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V375, independently written C11 FLVER2 bind pose matrix builder.
 * Original game assets used only for private verification, never published.
 */
#include "native_flver2_bind_pose_v375.h"
#include "native_flver2_geometry_v362.h"
#include <stdint.h>
#include <string.h>
#include <math.h>

#define BONE_BYTES_V375 128u
#define HEADER_BYTES_V375 128u

static uint32_t le32_v375(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static int16_t le16s_v375(const unsigned char *p) {
    uint16_t x=(uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
    return x<0x8000u ? (int16_t)x : (int16_t)((int32_t)x-0x10000);
}
static float lef_v375(const unsigned char *p) {
    uint32_t x=le32_v375(p);
    float f=0.0f;
    memcpy(&f,&x,sizeof f);
    return f;
}
static int range_v375(uint64_t off,uint64_t size,uint64_t limit) {
    return off<=limit && size<=limit-off;
}
static int overlap_v375(const void *a,size_t an,const void *b,size_t bn) {
    if (!an || !bn) return 0;
    if (!a || !b) return 1;
    const uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
    if (an>UINTPTR_MAX-av || bn>UINTPTR_MAX-bv) return 1;
    return av<bv+bn && bv<av+an;
}
static int bone_offset_v375(const ShytNativeFlver2GeometryV362 *g,
    uint32_t i,uint64_t *off) {
    uint64_t start=HEADER_BYTES_V375+
        (uint64_t)g->dummy_count*64u+(uint64_t)g->material_count*32u;
    uint64_t b=start+(uint64_t)i*BONE_BYTES_V375;
    if (!range_v375(b,BONE_BYTES_V375,g->data_offset)) return 0;
    *off=b;return 1;
}
static int valid_link_v375(int16_t n,uint32_t bones,uint32_t me) {
    return (n==-1) || (n>=0 && (uint32_t)n<bones && (uint32_t)n!=me);
}
static void ident_v375(float a[16]) {
    memset(a,0,16u*sizeof(float));
    a[0]=a[5]=a[10]=a[15]=1.0f;
}
static void multiply_v375(const float a[16],const float b[16],float out[16]) {
    float c[16];
    for(unsigned i=0;i<4u;++i) for(unsigned j=0;j<4u;++j) {
        double v=0.0;
        for(unsigned k=0;k<4u;++k)
            v+=(double)a[4u*i+k]*(double)b[4u*k+j];
        c[4u*i+j]=(float)v;
    }
    memcpy(out,c,sizeof c);
}
static void local_v375(float t[3],float r[3],float s[3],float m[16]) {
    float rx[16],rz[16],ry[16],scale[16],tr[16],tmp[16];
    ident_v375(rx);ident_v375(rz);ident_v375(ry);
    ident_v375(scale);ident_v375(tr);
    /* Row-vector FLVER Euler convention: scale, X, Z, Y, translate. */
    const float cx=cosf(r[0]),sx=sinf(r[0]);
    const float cz=cosf(r[2]),sz=sinf(r[2]);
    const float cy=cosf(r[1]),sy=sinf(r[1]);
    scale[0]=s[0];scale[5]=s[1];scale[10]=s[2];
    rx[5]=cx;rx[6]=sx;rx[9]=-sx;rx[10]=cx;
    rz[0]=cz;rz[1]=sz;rz[4]=-sz;rz[5]=cz;
    ry[0]=cy;ry[2]=-sy;ry[8]=sy;ry[10]=cy;
    tr[12]=t[0];tr[13]=t[1];tr[14]=t[2];
    multiply_v375(scale,rx,tmp);
    multiply_v375(tmp,rz,m);
    multiply_v375(m,ry,tmp);
    multiply_v375(tmp,tr,m);
}
static int finite_matrix_v375(const float m[16]) {
    for(unsigned j=0;j<16u;++j) if(!isfinite(m[j])) return 0;
    return 1;
}
static int valid_name_v375(const unsigned char *p,uint32_t offset,
                            uint32_t begin,uint32_t end) {
    if (offset<begin || offset>=end || (offset&1u)) return 0;
    /* UTF16LE file-level Unicode is mandatory in V362's narrow subset. */
    for(uint32_t j=offset;j+1u<end;j+=2u)
        if(p[j]==0 && p[j+1u]==0) return 1;
    return 0;
}
static int skeleton_preflight_v375(const unsigned char *p,size_t bytes,
    const ShytNativeFlver2GeometryV362 *g,uint32_t *roots,uint32_t *depth) {
    const uint32_t count=g->bone_count;
    const uint64_t fixed_end=HEADER_BYTES_V375+
        (uint64_t)g->dummy_count*64u+(uint64_t)g->material_count*32u+
        (uint64_t)g->bone_count*BONE_BYTES_V375+
        (uint64_t)g->mesh_count*48u+(uint64_t)g->face_set_count*32u+
        (uint64_t)g->vertex_buffer_count*32u+
        (uint64_t)g->layout_count*16u+(uint64_t)g->texture_count*32u;
    if(fixed_end>g->data_offset) return 0;
    *roots=0;*depth=0;
    for(uint32_t i=0;i<count;++i) {
        uint64_t off=0;
        if(!bone_offset_v375(g,i,&off)) return 0;
        int16_t parent=le16s_v375(p+off+28),child=le16s_v375(p+off+30);
        int16_t next=le16s_v375(p+off+44),prev=le16s_v375(p+off+46);
        if(!valid_link_v375(parent,count,i) ||
           !valid_link_v375(child,count,i) ||
           !valid_link_v375(next,count,i) ||
           !valid_link_v375(prev,count,i) ||
           !valid_name_v375(p,le32_v375(p+off+12),
                                (uint32_t)fixed_end,g->data_offset)) return 0;
        if (parent==-1) ++(*roots);
        const unsigned fields[]={0,16,32};
        for(unsigned f=0;f<3u;++f)
            for(unsigned k=0;k<3u;++k)
                if(!isfinite(lef_v375(p+off+fields[f]+4u*k))) return 0;
        /* Check all linked-list hints agree with authoritative parent. */
        if(child>=0) {
            uint64_t v=0;
            if(!bone_offset_v375(g,(uint32_t)child,&v) ||
               le16s_v375(p+v+28)!= (int16_t)i ||
               le16s_v375(p+v+46)!=-1) return 0;
        }
        if(next>=0) {
            uint64_t v=0;
            if(!bone_offset_v375(g,(uint32_t)next,&v) ||
               le16s_v375(p+v+28)!=parent ||
               le16s_v375(p+v+46)!=(int16_t)i) return 0;
        }
        if(prev>=0) {
            uint64_t v=0;
            if(!bone_offset_v375(g,(uint32_t)prev,&v) ||
               le16s_v375(p+v+28)!=parent ||
               le16s_v375(p+v+44)!=(int16_t)i) return 0;
        }
        /* A parent link must actually be reachable from that parent's
         * child/sibling chain, not merely an orphaned back-reference. */
        if(parent>=0) {
            uint64_t po=0;
            if(!bone_offset_v375(g,(uint32_t)parent,&po)) return 0;
            int32_t cursor=le16s_v375(p+po+30);
            uint32_t hops=0;
            while(cursor>=0 && cursor!=(int32_t)i) {
                if(hops++>=count) return 0; /* sibling cycle */
                uint64_t co=0;
                if(!bone_offset_v375(g,(uint32_t)cursor,&co)) return 0;
                cursor=le16s_v375(p+co+44);
            }
            if(cursor!=(int32_t)i) return 0;
        }
        uint32_t distance=0;
        int32_t walk=(int32_t)i;
        while(walk!=-1) {
            if(distance++>=count) return 0; /* parent graph cycle */
            uint64_t v=0;
            if(!bone_offset_v375(g,(uint32_t)walk,&v)) return 0;
            walk=le16s_v375(p+v+28);
            if (walk<-1 || (walk>=0 && (uint32_t)walk>=count)) return 0;
        }
        if(distance-1u>*depth) *depth=distance-1u;
    }
    (void)bytes;
    return 1;
}
int shyt_native_flver2_bind_pose_v375(const void *flver,size_t bytes,
    ShytNativeFlver2BonePoseV375 *poses,size_t capacity,
    ShytNativeFlver2SkeletonStatsV375 *stats) {
    if(!stats) return 0;
    if(flver && overlap_v375(flver,bytes,stats,sizeof *stats)) return 0;
    if(poses && capacity>SIZE_MAX/sizeof *poses) return 0;
    if(poses && overlap_v375(poses,capacity*sizeof *poses,stats,sizeof *stats)) return 0;
    if(flver && poses && overlap_v375(flver,bytes,poses,
                                      capacity*sizeof *poses)) return 0;
    memset(stats,0,sizeof *stats);
    if(!flver) return 0;
    ShytNativeFlver2GeometryV362 g={0};
    if(!shyt_native_flver2_geometry_probe_v362(flver,bytes,&g) ||
       g.bone_count>SHYT_NATIVE_V375_MAX_BONES ||
       (g.bone_count && (!poses || capacity<g.bone_count))) return 0;
    const unsigned char *p=(const unsigned char*)flver;
    uint32_t roots=0,depth=0;
    if(!skeleton_preflight_v375(p,bytes,&g,&roots,&depth)) return 0;
    if(g.bone_count && !roots) return 0;
    /* All pointer and cycle checks completed before writing any pose. */
    for(uint32_t i=0;i<g.bone_count;++i) {
        uint64_t off=0;bone_offset_v375(&g,i,&off);
        ShytNativeFlver2BonePoseV375 *o=&poses[i];
        memset(o,0,sizeof *o);
        o->parent=le16s_v375(p+off+28);
        o->first_child=le16s_v375(p+off+30);
        o->next_sibling=le16s_v375(p+off+44);
        o->previous_sibling=le16s_v375(p+off+46);
        for(unsigned c=0;c<3u;++c) {
            o->translation[c]=lef_v375(p+off+4u*c);
            o->rotation_xzy[c]=lef_v375(p+off+16u+4u*c);
            o->scale[c]=lef_v375(p+off+32u+4u*c);
        }
        uint32_t d=0;int32_t walk=o->parent;
        while(walk!=-1) {
            uint64_t v=0;bone_offset_v375(&g,(uint32_t)walk,&v);
            ++d; walk=le16s_v375(p+v+28);
        }
        o->depth=d;
        local_v375(o->translation,o->rotation_xzy,o->scale,o->local);
        if(!finite_matrix_v375(o->local)) {
            memset(poses,0,(size_t)g.bone_count*sizeof *poses);
            return 0;
        }
    }
    /* Parent can appear after child. Process by depth, not file order. */
    for(uint32_t level=0;level<=depth;++level) {
        for(uint32_t i=0;i<g.bone_count;++i) {
            ShytNativeFlver2BonePoseV375 *o=&poses[i];
            if(o->depth!=level) continue;
            if(o->parent<0) memcpy(o->world,o->local,sizeof o->world);
            else multiply_v375(o->local,poses[(uint32_t)o->parent].world,o->world);
            if(!finite_matrix_v375(o->world)) {
                memset(poses,0,(size_t)g.bone_count*sizeof *poses);
                return 0;
            }
        }
    }
    stats->bone_count=g.bone_count;
    stats->root_count=roots;
    stats->max_depth=depth;
    return 1;
}
