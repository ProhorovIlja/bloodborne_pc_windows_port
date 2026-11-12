/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic only: independent FLVER2 face list, strips and LOD/motion.
 */
#include "native_flver2_mesh_topology_v374.h"
#include "native_flver2_geometry_v362.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define DATA 0x220u
#define FILE_BYTES (DATA+124u)
static void w16(unsigned char *p,size_t pos,uint16_t x){p[pos]=(unsigned char)x;p[pos+1]=(unsigned char)(x>>8);}
static void w32(unsigned char *p,size_t pos,uint32_t x){w16(p,pos,(uint16_t)x);w16(p,pos+2,(uint16_t)(x>>16));}
static void fixture(unsigned char p[FILE_BYTES]){
    memset(p,0,FILE_BYTES);
    memcpy(p,"FLVER\0L\0",8);
    w32(p,8,0x20014u);
    w32(p,12,DATA);w32(p,16,124);
    w32(p,24,1);w32(p,32,1);w32(p,36,1);
    p[0x49]=1;
    w32(p,0x50,3);w32(p,0x54,1);
    /* mesh record at 0xa0; one material, no bones. */
    p[0xa0]=1;
    w32(p,0xa0+16,UINT32_MAX);
    w32(p,0xa0+32,3);w32(p,0xa0+36,0x170);
    w32(p,0xa0+40,1);w32(p,0xa0+44,0x180);
    w32(p,0x170,0);w32(p,0x174,1);w32(p,0x178,2);w32(p,0x180,0);
    /* first list; two visible triangles, R16 */
    p[0xd0+5]=1;
    w32(p,0xd0+8,6);w32(p,0xd0+12,0);w32(p,0xd0+16,12);
    w32(p,0xd0+24,16);
    /* second strip with reset (LOD1, R16) */
    w32(p,0xf0+0,0x01000000u);p[0xf0+4]=1;p[0xf0+5]=1;
    w32(p,0xf0+8,8);w32(p,0xf0+12,12);w32(p,0xf0+16,16);
    w32(p,0xf0+24,16);
    /* third 32-bit list, motion blur plus degenerate */
    w32(p,0x110,0x80000000u);p[0x110+5]=1;
    w32(p,0x110+8,6);w32(p,0x110+12,28);w32(p,0x110+16,24);
    w32(p,0x110+24,32);
    /* single VB / layout */
    w32(p,0x130+8,12);w32(p,0x130+12,6);
    w32(p,0x130+24,72);w32(p,0x130+28,52);
    w32(p,0x150,1);w32(p,0x150+12,0x190);
    w32(p,0x190+8,2);/* Float3 */
    const uint16_t base[]={0,1,2,2,3,4};
    for(unsigned i=0;i<6;++i) w16(p,DATA+2u*i,base[i]);
    const uint16_t strip[]={0,1,2,3,0xffffu,1,3,4};
    for(unsigned i=0;i<8;++i) w16(p,DATA+12u+2u*i,strip[i]);
    const uint32_t motion[]={0,1,2,2,2,5};
    for(unsigned i=0;i<6;++i) w32(p,DATA+28u+4u*i,motion[i]);
}
static void positive(void){
    unsigned char p[FILE_BYTES];fixture(p);
    ShytNativeFlver2GeometryV362 g={0};
    assert(shyt_native_flver2_geometry_probe_v362(p,sizeof p,&g));
    assert(g.mesh_count==1 && g.face_set_count==3 && g.total_vertices==6);
    ShytNativeMeshFaceV374 info={0};
    assert(shyt_native_flver2_mesh_face_v374(p,sizeof p,0,0,&info));
    assert(info.mesh_index==0 && info.face_set_index==0 &&
           info.material_index==0 && info.default_bone_index==-1 &&
           info.vertex_count==6 && info.vertex_buffer_count==1 &&
           info.vertex_buffer_indices[0]==0 && info.lod==SHYT_V374_LOD_BASE &&
           info.motion_blur==0 && info.triangle_strip==0 &&
           info.cull_backfaces==1 && info.triangle_count==2);
    uint32_t out[12]={0};
    assert(shyt_native_flver2_triangles_v374(p,sizeof p,0,0,out,12,&info));
    const uint32_t expected_list[]={0,1,2,2,3,4};
    assert(memcmp(out,expected_list,sizeof expected_list)==0);
    assert(shyt_native_flver2_mesh_face_v374(p,sizeof p,0,1,&info));
    assert(info.lod==SHYT_V374_LOD1 && info.triangle_strip &&
           info.triangle_count==3 && info.restart_count==1);
    assert(shyt_native_flver2_triangles_v374(p,sizeof p,0,1,out,12,&info));
    const uint32_t expected_strip[]={0,1,2,2,1,3,1,3,4};
    assert(memcmp(out,expected_strip,sizeof expected_strip)==0);
    assert(shyt_native_flver2_mesh_face_v374(p,sizeof p,0,2,&info));
    assert(info.motion_blur==1 && info.lod==0 && info.index_element_bytes==4 &&
           info.degenerate_count==1 && info.triangle_count==1);
    assert(shyt_native_flver2_triangles_v374(p,sizeof p,0,2,out,12,&info));
    assert(out[0]==0 && out[1]==1 && out[2]==2);
    assert(shyt_native_flver2_triangles_v374(p,sizeof p,0,2,NULL,0,&info));
    assert(info.triangle_count==1);
}
static void negatives(void){
    unsigned char p[FILE_BYTES];fixture(p);
    ShytNativeMeshFaceV374 info={0};uint32_t out[16];
    memset(out,0xa5,sizeof out);
    assert(!shyt_native_flver2_triangles_v374(p,sizeof p,0,1,out,8,&info));
    assert(info.triangle_count==0);
    uint32_t hold[16];memset(hold,0xa5,sizeof hold);
    assert(memcmp(out,hold,sizeof hold)==0); /* no partial writes */
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,1,0,&info));
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,3,&info));
    assert(!shyt_native_flver2_triangles_v374(p,sizeof p,0,0,
               (uint32_t*)(void*)(p+DATA),6,&info));
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,0,
               (ShytNativeMeshFaceV374*)(void*)(p+32)));
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p-1,0,0,&info));
    assert(!shyt_native_flver2_triangles_v374(p,sizeof p,0,0,out,16,
               (ShytNativeMeshFaceV374*)(void*)out));
    /* Future LODEx unsupported rather than silently rendering wrong LOD. */
    w32(p,0xd0,0x04000000u);
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,0,&info));
    fixture(p);
    w32(p,0xd0,0x03000000u); /* LOD1 and LOD2 simultaneously */
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,0,&info));
    fixture(p);
    w32(p,0xd0+8,5);w32(p,0xd0+16,10); /* odd trailing list */
    assert(shyt_native_flver2_geometry_probe_v362(p,sizeof p,&(ShytNativeFlver2GeometryV362){0}));
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,0,&info));
    fixture(p);
    w16(p,DATA,0xffffu); /* A list may never contain restart sentinel */
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,0,&info));
    fixture(p);
    w32(p,DATA+28,UINT32_MAX);
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,2,&info));
    fixture(p);
    p[DATA+12+4]=0xff;p[DATA+12+5]=0xff; /* original strip restart: accepted */
    assert(shyt_native_flver2_mesh_face_v374(p,sizeof p,0,1,&info));
    fixture(p);
    /* A strip's degenerate triples still change winding parity. */
    p[0x110+4]=1;
    const uint32_t deg_strip[]={0,1,2,2,3,4};
    for(unsigned i=0;i<6;++i) w32(p,DATA+28u+4u*i,deg_strip[i]);
    assert(shyt_native_flver2_triangles_v374(p,sizeof p,0,2,out,16,&info));
    assert(info.triangle_count==2 && info.degenerate_count==2 &&
           info.restart_count==0);
    const uint32_t expected_flip[]={0,1,2,3,2,4};
    assert(memcmp(out,expected_flip,sizeof expected_flip)==0);
    fixture(p);
    p[0x110+4]=1;
    const uint32_t restart32[]={0,1,2,UINT32_MAX,1,3};
    for(unsigned i=0;i<6;++i) w32(p,DATA+28u+4u*i,restart32[i]);
    assert(shyt_native_flver2_mesh_face_v374(p,sizeof p,0,2,&info));
    assert(info.triangle_count==1 && info.restart_count==1);
    fixture(p);
    w32(p,0x110,0x82000000u);
    assert(shyt_native_flver2_mesh_face_v374(p,sizeof p,0,2,&info));
    assert(info.lod==SHYT_V374_LOD2 && info.motion_blur==1);
    fixture(p);
    w16(p,DATA+12,7);
    assert(!shyt_native_flver2_mesh_face_v374(p,sizeof p,0,1,&info));
}
int main(void){positive();negatives();puts("NATIVE_V374_SYNTHETIC_MESH_LOD_STRIP_INDEX_TOPOLOGY_PASS");return 0;}
