/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic only. Bone graph, matrix order, invalid links and aliasing.
 * No Bloodborne or Dark Souls III assets are included.
 */
#include "native_flver2_bind_pose_v375.h"
#include "native_flver2_geometry_v362.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define BONES 3u
#define BONE_START 0x80u
#define NAME_START (BONE_START+BONES*128u)
#define DATA_START 0x240u
static void wr16(unsigned char *p,size_t off,uint16_t n) {
    p[off]=(unsigned char)n;p[off+1u]=(unsigned char)(n>>8);
}
static void wr32(unsigned char *p,size_t off,uint32_t n) {
    wr16(p,off,(uint16_t)n);wr16(p,off+2u,(uint16_t)(n>>16));
}
static void wrf(unsigned char *p,size_t off,float f) {
    uint32_t x=0;memcpy(&x,&f,sizeof f);wr32(p,off,x);
}
static void name(unsigned char *p,size_t off,const char *s) {
    while(*s) {p[off++]=(unsigned char)*s++;p[off++]=0u;}
    p[off]=p[off+1u]=0;
}
static void bone(unsigned char *p,uint32_t i,int16_t parent,int16_t child,
                 int16_t next,int16_t prev,uint32_t nameoff) {
    const size_t off=BONE_START+(size_t)i*128u;
    wr32(p,off+12,nameoff);
    wr16(p,off+28,(uint16_t)parent);wr16(p,off+30,(uint16_t)child);
    wr16(p,off+44,(uint16_t)next);wr16(p,off+46,(uint16_t)prev);
    for(unsigned j=0;j<3u;++j) wrf(p,off+32u+4u*j,1.0f);
}
static void fixture(unsigned char p[DATA_START]) {
    memset(p,0,DATA_START);
    memcpy(p,"FLVER\0L\0",8);
    wr32(p,8,0x20014u);wr32(p,12,DATA_START);
    wr32(p,28,BONES);p[0x49]=1; /* Unicode */
    bone(p,0,-1,1,-1,-1,NAME_START);
    bone(p,1,0,-1,2,-1,NAME_START+16);
    bone(p,2,0,-1,-1,1,NAME_START+32);
    name(p,NAME_START,"root");
    name(p,NAME_START+16,"child");
    name(p,NAME_START+32,"sibling");
    wrf(p,BONE_START+0,1.0f); /* root x translation = 1 */
    wrf(p,BONE_START+16+8,1.5707963267948966f); /* z Euler angle */
    wrf(p,BONE_START+128+4,2.0f); /* child local y translation */
    wrf(p,BONE_START+256+4,3.0f); /* sibling local y translation */
}
static int approx(float a,float b) {return fabsf(a-b)<0.0002f;}
static void positive(void) {
    unsigned char p[DATA_START];fixture(p);
    ShytNativeFlver2BonePoseV375 out[BONES];
    ShytNativeFlver2SkeletonStatsV375 stats={0};
    assert(shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    assert(stats.bone_count==3 && stats.root_count==1 && stats.max_depth==1);
    assert(out[0].depth==0 && out[1].depth==1 && out[2].depth==1);
    assert(out[0].parent==-1 && out[0].first_child==1);
    assert(out[1].next_sibling==2 && out[2].previous_sibling==1);
    assert(approx(out[0].world[12],1.0f)&&approx(out[0].world[13],0.0f));
    assert(approx(out[1].world[12],-1.0f)&&approx(out[1].world[13],0.0f));
    assert(approx(out[2].world[12],-2.0f)&&approx(out[2].world[13],0.0f));
    assert(approx(out[0].world[0],0.0f) && approx(out[0].world[1],1.0f));
    /* Parent indices need not precede child records. */
    bone(p,0,-1,2,-1,-1,NAME_START);
    bone(p,1,2,-1,-1,-1,NAME_START+16);
    bone(p,2,0,1,-1,-1,NAME_START+32);
    assert(shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    assert(stats.max_depth==2 && out[1].depth==2 && out[2].depth==1);
    assert(approx(out[1].world[12],-4.0f));
    /* Empty valid skeleton is accepted without any output storage. */
    unsigned char empty[0x80]={0};
    memcpy(empty,"FLVER\0L\0",8);wr32(empty,8,0x20014u);
    wr32(empty,12,0x80);empty[0x49]=1;
    assert(shyt_native_flver2_bind_pose_v375(empty,sizeof empty,NULL,0,&stats));
    assert(stats.bone_count==0 && stats.max_depth==0);
}
static void negatives(void) {
    unsigned char p[DATA_START];fixture(p);
    ShytNativeFlver2BonePoseV375 out[BONES];
    ShytNativeFlver2BonePoseV375 snapshot[BONES];
    ShytNativeFlver2SkeletonStatsV375 stats={8,8,8};
    memset(out,0xA5,sizeof out);memcpy(snapshot,out,sizeof out);
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES-1,&stats));
    assert(stats.bone_count==0 && memcmp(out,snapshot,sizeof out)==0);
    fixture(p);wr16(p,BONE_START+28,1); /* parent 0->1->0: cycle */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    assert(memcmp(out,snapshot,sizeof out)==0);
    fixture(p);wr16(p,BONE_START+128+28,999); /* out-of-range parent */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);wr16(p,BONE_START+256+46,0); /* sibling link mismatch */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);wr16(p,BONE_START+30,2); /* wrong head-of-child-chain */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);wr16(p,BONE_START+30,(uint16_t)-1); /* orphan children */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);wr32(p,BONE_START+12,0x80); /* name points to bone metadata */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);wr32(p,BONE_START+12,DATA_START-2); /* no room for terminator */
    p[DATA_START-2]=1;p[DATA_START-1]=0;
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);wr32(p,BONE_START+16,0x7fc00000u); /* NaN rotation */
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,&stats));
    fixture(p);
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,
        (ShytNativeFlver2BonePoseV375*)(void*)(p+128),BONES,&stats));
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,
        (ShytNativeFlver2SkeletonStatsV375*)(void*)out));
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,
        (ShytNativeFlver2SkeletonStatsV375*)(void*)p));
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p,out,BONES,NULL));
    assert(!shyt_native_flver2_bind_pose_v375(p,sizeof p-1,out,BONES,&stats));
}
int main(void) {
    positive();negatives();
    puts("NATIVE_V375_SYNTHETIC_FLVER_BONE_HIERARCHY_BIND_POSE_PASS");
    return 0;
}
