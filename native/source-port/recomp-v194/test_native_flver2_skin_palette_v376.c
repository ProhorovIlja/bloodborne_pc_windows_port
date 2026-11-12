/* SPDX-License-Identifier: GPL-2.0-or-later
 * V376 public synthetic FLVER palette, matrix inversion, weighted positions.
 * No original game assets or proprietary executable content.
 */
#include "native_flver2_skin_palette_v376.h"
#include "native_flver2_geometry_v362.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define DATA 0x300u
#define SIZE (DATA+64u)
#define MESH 0x1a0u
#define FACE 0x1d0u
#define VB 0x1f0u
#define LAYOUT 0x210u
static void w16(unsigned char *p,size_t i,uint16_t v) {p[i]=(unsigned char)v;p[i+1u]=(unsigned char)(v>>8);}
static void w32(unsigned char *p,size_t i,uint32_t v) {w16(p,i,(uint16_t)v);w16(p,i+2u,(uint16_t)(v>>16));}
static void wf(unsigned char *p,size_t i,float f) {uint32_t x=0;memcpy(&x,&f,sizeof x);w32(p,i,x);}
static void bone(unsigned char *p,size_t off,uint32_t name,int16_t parent,int16_t child) {
    w32(p,off+12u,name);
    w16(p,off+28u,(uint16_t)parent);w16(p,off+30u,(uint16_t)child);
    w16(p,off+44u,UINT16_MAX);w16(p,off+46u,UINT16_MAX);
    for(unsigned i=0;i<3;++i)wf(p,off+32u+4u*i,1.0f);
}
static void fixture(unsigned char p[SIZE]) {
    memset(p,0,SIZE);memcpy(p,"FLVER\0L\0",8);
    w32(p,8,0x20014u);w32(p,12,DATA);w32(p,16,64u);
    w32(p,24,1);w32(p,28,2);w32(p,32,1);w32(p,36,1);
    p[0x49]=1;w32(p,0x50,1);w32(p,0x54,1);
    bone(p,0xa0,0x270,-1,1);bone(p,0x120,0x280,0,-1);
    p[MESH]=1;
    w32(p,MESH+4,0);w32(p,MESH+16,0);
    w32(p,MESH+20,2);w32(p,MESH+28,0x250);
    w32(p,MESH+32,1);w32(p,MESH+36,0x258);
    w32(p,MESH+40,1);w32(p,MESH+44,0x25c);
    w32(p,0x250,0);w32(p,0x254,1);w32(p,0x258,0);w32(p,0x25c,0);
    p[FACE+5]=1;w32(p,FACE+8,3);w32(p,FACE+16,6);w32(p,FACE+24,16);
    w32(p,VB+4,0);w32(p,VB+8,12);w32(p,VB+12,3);
    w32(p,VB+24,36);w32(p,VB+28,16);
    w32(p,LAYOUT,1);w32(p,LAYOUT+12,0x230);
    w32(p,0x230+8,2); /* Float3 position, semantic0 */
    const char *str0="root",*str1="child";
    for(unsigned i=0;str0[i];++i) {p[0x270+i*2]=(unsigned char)str0[i];}
    for(unsigned i=0;str1[i];++i) {p[0x280+i*2]=(unsigned char)str1[i];}
    /* FLVER file data: 3 indices and three float3 vertices. */
    w16(p,DATA,0);w16(p,DATA+2,1);w16(p,DATA+4,2);
    wf(p,DATA+16,3.0f);wf(p,DATA+16+12,4.0f);wf(p,DATA+16+24,5.0f);
}
static int near(float a,float b){return fabsf(a-b)<0.0005f;}
static void identity(float m[16]) {memset(m,0,16u*sizeof(float));m[0]=m[5]=m[10]=m[15]=1;}
static void matrix_mul(const float a[16],const float b[16],float out[16]) {
    for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c) {
        double s=0;for(unsigned k=0;k<4;++k)s+=(double)a[4u*r+k]*b[4u*k+c];
        out[4u*r+c]=(float)s;
    }
}
static void palette(void) {
    unsigned char p[SIZE];fixture(p);
    ShytNativeFlver2GeometryV362 g={0};
    assert(shyt_native_flver2_geometry_probe_v362(p,sizeof p,&g));
    assert(g.bone_count==2 && g.mesh_count==1 && g.total_vertices==3);
    uint32_t indices[3]={9,9,9};
    ShytNativeMeshPaletteInfoV376 info={0};
    assert(shyt_native_flver2_mesh_palette_v376(p,sizeof p,0,indices,3,&info));
    assert(info.mesh_index==0 && info.entries==2 && info.global_bones==2 &&
           info.default_bone==0 && info.dynamic_flag==1);
    assert(indices[0]==0 && indices[1]==1 && indices[2]==9);
    uint32_t before[3];memcpy(before,indices,sizeof before);
    assert(!shyt_native_flver2_mesh_palette_v376(p,sizeof p,0,indices,1,&info));
    assert(info.entries==0 && !memcmp(indices,before,sizeof before));
    assert(!shyt_native_flver2_mesh_palette_v376(p,sizeof p,1,indices,3,&info));
    assert(!shyt_native_flver2_mesh_palette_v376(p,sizeof p,0,
          (uint32_t*)(void*)(p+DATA),3,&info));
    fixture(p);w32(p,0x254,999);
    assert(!shyt_native_flver2_mesh_palette_v376(p,sizeof p,0,indices,3,&info));
    assert(!memcmp(indices,before,sizeof before));
    fixture(p);w32(p,MESH+20,0);w32(p,MESH+28,0);
    assert(shyt_native_flver2_mesh_palette_v376(p,sizeof p,0,NULL,0,&info));
    assert(info.entries==0 && info.default_bone==0);
}
static void inverse(void) {
    ShytNativeFlver2BonePoseV375 poses[3]={0};
    for(unsigned i=0;i<3;++i)identity(poses[i].world);
    poses[0].world[12]=1;
    poses[1].world[12]=1;poses[1].world[13]=2;
    /* Nonuniform scale * quarter turn around Z, then translation. */
    poses[2].world[0]=0;poses[2].world[1]=2;
    poses[2].world[4]=-3;poses[2].world[5]=0;
    poses[2].world[10]=4;poses[2].world[12]=5;poses[2].world[13]=-2;
    float inv[3][16];
    assert(shyt_native_flver2_inverse_binds_v376(poses,3,inv,3));
    for(unsigned m=0;m<3;++m) {
        float got[16];matrix_mul(poses[m].world,inv[m],got);
        for(unsigned k=0;k<16;++k)
            assert(near(got[k],k%5u==0u?1.0f:0.0f));
    }
    float saved[3][16];memcpy(saved,inv,sizeof inv);
    assert(!shyt_native_flver2_inverse_binds_v376(poses,3,inv,2));
    assert(!memcmp(saved,inv,sizeof inv));
    poses[2].world[0]=0;poses[2].world[1]=0;poses[2].world[4]=0;
    assert(!shyt_native_flver2_inverse_binds_v376(poses,3,inv,3));
    assert(!memcmp(saved,inv,sizeof inv));
    poses[2].world[0]=1;poses[2].world[1]=0;
    poses[2].world[4]=0;poses[2].world[5]=1;
    poses[2].world[3]=1; /* non-affine */
    assert(!shyt_native_flver2_inverse_binds_v376(poses,3,inv,3));
    poses[2].world[3]=0;
    poses[2].world[0]=NAN;
    assert(!shyt_native_flver2_inverse_binds_v376(poses,3,inv,3));
    assert(shyt_native_flver2_inverse_binds_v376(NULL,0,NULL,0));
    assert(!shyt_native_flver2_inverse_binds_v376(poses,3,(float (*)[16])(void*)poses,3));
}
static void skin(void) {
    uint32_t palette[2]={0,1};
    ShytNativeFlver2BonePoseV375 pose[2]={0};
    identity(pose[0].world);identity(pose[1].world);
    pose[0].world[12]=1;pose[1].world[12]=1;pose[1].world[13]=2;
    float inverse[2][16],animated[2][16];
    assert(shyt_native_flver2_inverse_binds_v376(pose,2,inverse,2));
    memcpy(animated[0],pose[0].world,sizeof animated[0]);
    memcpy(animated[1],pose[1].world,sizeof animated[1]);
    ShytNativeFlver2VertexV371 v[2]={0};
    ShytNativeSkinnedPositionV376 out[2]={{ {777,777,777} },{{888,888,888}}};
    for(unsigned i=0;i<2;++i) {
        v[i].present=SHYT_V371_BONE_INDICES|SHYT_V371_BONE_WEIGHTS;
        v[i].position[0]=3;v[i].position[1]=0;v[i].position[2]=0;
        v[i].bone_indices[0]=1;v[i].bone_weights[0]=1;
    }
    assert(shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    assert(near(out[0].xyz[0],3) && near(out[0].xyz[1],0));
    animated[1][13]=4;
    assert(shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    assert(near(out[0].xyz[0],3)&&near(out[0].xyz[1],2));
    v[0].bone_indices[0]=0;v[0].bone_weights[0]=0.5f;
    v[0].bone_indices[1]=1;v[0].bone_weights[1]=0.5f;
    assert(shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    assert(near(out[0].xyz[0],3)&&near(out[0].xyz[1],1));
    /* A model with a separately verified empty local palette may choose
     * global indices explicitly; no source-driven silent fallback. */
    v[0].bone_indices[0]=1;v[0].bone_weights[0]=1.0f;
    v[0].bone_indices[1]=0;v[0].bone_weights[1]=0.0f;
    assert(shyt_native_flver2_skin_global_positions_v376(
        v,2,(const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    assert(near(out[0].xyz[0],3) && near(out[0].xyz[1],2));
    assert(!shyt_native_flver2_skin_global_positions_v376(
        v,2,(const float (*)[16])inverse,(const float (*)[16])animated,0,out,2));
    v[0].bone_indices[0]=0;v[0].bone_weights[0]=0.5f;
    v[0].bone_indices[1]=1;v[0].bone_weights[1]=0.5f;
    assert(shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    ShytNativeSkinnedPositionV376 snap[2];memcpy(snap,out,sizeof snap);
    v[1].bone_indices[0]=2;
    assert(!shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    assert(!memcmp(out,snap,sizeof snap));
    v[1].bone_indices[0]=1;
    assert(!shyt_native_flver2_skin_positions_v376(v,2,NULL,0,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    assert(!memcmp(out,snap,sizeof snap));
    v[1].bone_weights[0]=0;
    assert(!shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    v[1].bone_weights[0]=1;
    v[1].position[0]=NAN;
    assert(!shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,out,2));
    v[1].position[0]=3;
    assert(!shyt_native_flver2_skin_positions_v376(v,2,palette,2,
            (const float (*)[16])inverse,(const float (*)[16])animated,2,
            (ShytNativeSkinnedPositionV376*)(void*)v,2));
}
int main(void){palette();inverse();skin();
    puts("NATIVE_V376_PALETTE_INVERSE_BIND_WEIGHTED_CPU_SKIN_PASS");return 0;}
