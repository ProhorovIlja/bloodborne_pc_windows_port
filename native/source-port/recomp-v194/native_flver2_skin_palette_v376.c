/* SPDX-License-Identifier: GPL-2.0-or-later
 * V376. Independent C11 skeletal palette/inverse bind diagnostic subsystem.
 * No original game data, gameplay, PS4 ABI or external code copied.
 */
#include "native_flver2_skin_palette_v376.h"
#include "native_flver2_geometry_v362.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

static uint32_t le32_v376(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static int ranges_v376(uint64_t off,uint64_t n,uint64_t end) {
    return off<=end && n<=end-off;
}
static int overlaps_v376(const void *a,size_t an,const void *b,size_t bn) {
    if (!an || !bn) return 0;
    if (!a || !b) return 1;
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    if (an>UINTPTR_MAX-x || bn>UINTPTR_MAX-y) return 1;
    return x<y+bn && y<x+an;
}
static int bytes_v376(size_t n,size_t item,size_t *total) {
    if (item && n>SIZE_MAX/item) return 0;
    *total=n*item;
    return 1;
}
int shyt_native_flver2_mesh_palette_v376(
    const void *flver,size_t bytes,uint32_t mesh,
    uint32_t *global_bones,size_t capacity,
    ShytNativeMeshPaletteInfoV376 *info) {
    if (!info) return 0;
    size_t out_bytes=0;
    if (!bytes_v376(capacity,sizeof(uint32_t),&out_bytes) ||
        (flver && overlaps_v376(flver,bytes,info,sizeof *info)) ||
        (global_bones && overlaps_v376(info,sizeof *info,global_bones,out_bytes)) ||
        (flver && global_bones && overlaps_v376(flver,bytes,global_bones,out_bytes))) return 0;
    memset(info,0,sizeof *info);
    ShytNativeFlver2GeometryV362 g={0};
    if (!flver || !shyt_native_flver2_geometry_probe_v362(flver,bytes,&g) ||
        mesh>=g.mesh_count || g.bone_count>SHYT_NATIVE_V376_MAX_BONES) return 0;
    const unsigned char *p=(const unsigned char *)flver;
    uint64_t off=(uint64_t)g.first_mesh_record_offset+(uint64_t)mesh*48u;
    if (!ranges_v376(off,48u,g.data_offset)) return 0;
    uint32_t count=le32_v376(p+off+20);
    uint32_t off_palette=le32_v376(p+off+28);
    if (count>SHYT_NATIVE_V376_MAX_BONES ||
        (count && (!global_bones || count>capacity)) ||
        (count && !ranges_v376(off_palette,(uint64_t)count*4u,g.data_offset))) return 0;
    /* Preflight the complete array before touching caller-owned storage.
     * V362 also verifies this; the second check makes this API standalone
     * against any future relaxation of the generic parser. */
    for(uint32_t i=0;i<count;++i) {
        uint32_t index=le32_v376(p+(uint64_t)off_palette+4u*i);
        if (index>=g.bone_count) return 0;
    }
    for(uint32_t i=0;i<count;++i)
        global_bones[i]=le32_v376(p+(uint64_t)off_palette+4u*i);
    info->mesh_index=mesh;
    info->entries=count;
    info->global_bones=g.bone_count;
    info->dynamic_flag=p[off];
    info->default_bone=(int32_t)le32_v376(p+off+16);
    return 1;
}
static int invert_affine_v376(const float in[16],float out[16]) {
    if (!in) return 0;
    for(unsigned i=0;i<16;++i) if (!isfinite(in[i])) return 0;
    if (fabs((double)in[3])>1e-6 || fabs((double)in[7])>1e-6 ||
        fabs((double)in[11])>1e-6 || fabs((double)in[15]-1.0)>1e-6)
        return 0;
    double a=in[0],b=in[1],c=in[2];
    double d=in[4],e=in[5],f=in[6];
    double g=in[8],h=in[9],i=in[10];
    double c00=e*i-f*h,c01=c*h-b*i,c02=b*f-c*e;
    double c10=f*g-d*i,c11=a*i-c*g,c12=c*d-a*f;
    double c20=d*h-e*g,c21=b*g-a*h,c22=a*e-b*d;
    double determinant=a*c00+b*c10+c*c20;
    double xnorm=sqrt(a*a+b*b+c*c);
    double ynorm=sqrt(d*d+e*e+f*f);
    double znorm=sqrt(g*g+h*h+i*i);
    double norm_product=xnorm*ynorm*znorm;
    if (!isfinite(determinant) || !isfinite(norm_product) ||
        norm_product<1e-24 || fabs(determinant)/norm_product<1e-9) return 0;
    /* Cofactor matrix transposed = inverse 3x3. Here cij are entries
     * of the adjugate already arranged row-by-row. */
    double v[16]={c00/determinant,c01/determinant,c02/determinant,0,
                  c10/determinant,c11/determinant,c12/determinant,0,
                  c20/determinant,c21/determinant,c22/determinant,0,
                  0,0,0,1};
    for(unsigned col=0;col<3;++col)
        v[12u+col]=-((double)in[12]*v[col]+(double)in[13]*v[4u+col]+(double)in[14]*v[8u+col]);
    for(unsigned k=0;k<16;++k) {
        if (!isfinite(v[k]) || fabs(v[k])>3.4028234663852886e38) return 0;
        out[k]=(float)v[k];
        if (!isfinite(out[k])) return 0;
    }
    /* Check both multiplication orders. A near-singular but formally
     * invertible matrix must not silently corrupt vertex positions. */
    for(unsigned row=0;row<4;++row)
        for(unsigned col=0;col<4;++col) {
            double left=0,right=0;
            for(unsigned k=0;k<4;++k) {
                left+=(double)in[4u*row+k]*out[4u*k+col];
                right+=(double)out[4u*row+k]*in[4u*k+col];
            }
            double expected=row==col?1.0:0.0;
            if (fabs(left-expected)>5e-4 || fabs(right-expected)>5e-4)
                return 0;
        }
    return 1;
}
int shyt_native_flver2_inverse_binds_v376(
    const ShytNativeFlver2BonePoseV375 *pose,size_t count,
    float (*inverse_bind)[16],size_t capacity) {
    size_t source_bytes=0,target_bytes=0;
    if (count>SHYT_NATIVE_V376_MAX_BONES || count>capacity ||
        !bytes_v376(count,sizeof *pose,&source_bytes) ||
        !bytes_v376(capacity,sizeof *inverse_bind,&target_bytes) ||
        (count && (!pose || !inverse_bind)) ||
        (pose && inverse_bind && overlaps_v376(pose,source_bytes,inverse_bind,target_bytes)))
        return 0;
    if (!count) return 1;
    float tmp[16];
    for(size_t b=0;b<count;++b)
        if (!invert_affine_v376(pose[b].world,tmp)) return 0;
    for(size_t b=0;b<count;++b) {
        if (!invert_affine_v376(pose[b].world,tmp)) return 0;
        memcpy(inverse_bind[b],tmp,sizeof tmp);
    }
    return 1;
}
static int finite_affine_v376(const float m[16]) {
    for(unsigned i=0;i<16;++i) if (!isfinite(m[i])) return 0;
    return fabsf(m[3])<1e-5f && fabsf(m[7])<1e-5f &&
           fabsf(m[11])<1e-5f && fabsf(m[15]-1.0f)<1e-5f;
}
static int valid_skin_input_v376(
    const ShytNativeFlver2VertexV371 *v,const uint32_t *palette,
    size_t palette_count,size_t global_count) {
    if ((v->present&(SHYT_V371_BONE_INDICES|SHYT_V371_BONE_WEIGHTS))!=
                    (SHYT_V371_BONE_INDICES|SHYT_V371_BONE_WEIGHTS)) return 0;
    double sum=0.0;
    for(unsigned k=0;k<3;++k) if (!isfinite(v->position[k])) return 0;
    for(unsigned k=0;k<4;++k) {
        const float weight=v->bone_weights[k];
        if (!isfinite(weight) || weight<0 || weight>1.0f) return 0;
        if (weight==0.0f) continue;
        if (v->bone_indices[k]>=palette_count ||
            palette[v->bone_indices[k]]>=global_count) return 0;
        sum+=weight;
    }
    return sum>0 && sum<=1.01;
}
static void skin_one_v376(
    const ShytNativeFlver2VertexV371 *v,const uint32_t *palette,
    const float (*inverse)[16],const float (*animated)[16],
    ShytNativeSkinnedPositionV376 *out) {
    double p[3]={0,0,0},sum=0;
    for(unsigned bone=0;bone<4;++bone) {
        double w=(double)v->bone_weights[bone];
        if (w==0) continue;
        uint32_t global=palette[v->bone_indices[bone]];
        double bind_local[3]={0,0,0};
        for(unsigned col=0;col<3;++col) {
            double q=inverse[global][12u+col];
            for(unsigned k=0;k<3;++k)
                q+=(double)v->position[k]*inverse[global][4u*k+col];
            bind_local[col]=q;
        }
        for(unsigned col=0;col<3;++col) {
            double q=(double)animated[global][12u+col];
            for(unsigned k=0;k<3;++k)
                q+=bind_local[k]*animated[global][4u*k+col];
            p[col]+=w*q;
        }
        sum+=w;
    }
    for(unsigned k=0;k<3;++k) out->xyz[k]=(float)(p[k]/sum);
}
int shyt_native_flver2_skin_positions_v376(
    const ShytNativeFlver2VertexV371 *vertices,size_t count,
    const uint32_t *palette,size_t palette_count,
    const float (*inverse)[16],const float (*animated)[16],size_t global_count,
    ShytNativeSkinnedPositionV376 *output,size_t capacity) {
    size_t vin=0,pbytes=0,matbytes=0,outs=0;
    if (count>1000000u || global_count>SHYT_NATIVE_V376_MAX_BONES ||
        palette_count>SHYT_NATIVE_V376_MAX_BONES || count>capacity ||
        !bytes_v376(count,sizeof *vertices,&vin) ||
        !bytes_v376(palette_count,sizeof *palette,&pbytes) ||
        !bytes_v376(global_count,sizeof *inverse,&matbytes) ||
        !bytes_v376(count,sizeof *output,&outs) ||
        (count && (!vertices || !output || !palette || !inverse || !animated)) ||
        (palette_count && !palette) || (global_count && (!inverse || !animated)) ||
        overlaps_v376(vertices,vin,output,outs) ||
        overlaps_v376(palette,pbytes,output,outs) ||
        overlaps_v376(inverse,matbytes,output,outs) ||
        overlaps_v376(animated,matbytes,output,outs))return 0;
    if (!count) return 1;
    if (!palette_count || !global_count) return 0;
    for(size_t b=0;b<global_count;++b)
        if (!finite_affine_v376(inverse[b]) || !finite_affine_v376(animated[b])) return 0;
    for(size_t v=0;v<count;++v) {
        ShytNativeSkinnedPositionV376 tmp;
        if (!valid_skin_input_v376(&vertices[v],palette,palette_count,global_count))return 0;
        skin_one_v376(&vertices[v],palette,inverse,animated,&tmp);
        for(unsigned k=0;k<3;++k)if(!isfinite(tmp.xyz[k]))return 0;
    }
    for(size_t v=0;v<count;++v)
        skin_one_v376(&vertices[v],palette,inverse,animated,&output[v]);
    return 1;
}
