/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic, source-only V364 GPU upload planning tests. Zero game bytes.
 */
#include "native_flver2_gpu_plan_v364.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define FILE_BYTES_V364 0x1b4u
#define VERTICES_OFF_V364 0x180u
static void write16_v364(unsigned char *p,size_t off,uint16_t n){
    p[off]=(unsigned char)n; p[off+1]=(unsigned char)(n>>8);
}
static void write32_v364(unsigned char *p,size_t off,uint32_t n){
    write16_v364(p,off,(uint16_t)n);write16_v364(p,off+2,(uint16_t)(n>>16));
}
static void invented_flver_v364(unsigned char *p){
    memset(p,0,FILE_BYTES_V364);
    memcpy(p,"FLVER\0L\0",8);
    write32_v364(p,8,0x20014);
    write32_v364(p,12,VERTICES_OFF_V364);
    write32_v364(p,16,52);
    write32_v364(p,24,1); /* material */
    write32_v364(p,32,1); /* mesh */
    write32_v364(p,36,1); /* vertex buffer */
    p[0x49]=1;
    write32_v364(p,0x50,1); /* face set */
    write32_v364(p,0x54,1); /* layout */
    p[0xa0]=1;
    write32_v364(p,0xa0+16,UINT32_MAX);
    write32_v364(p,0xa0+32,1);
    write32_v364(p,0xa0+36,0x138);
    write32_v364(p,0xa0+40,1);
    write32_v364(p,0xa0+44,0x13c);
    p[0xd0+4]=1; /* triangle strip */
    p[0xd0+5]=1; /* cull backfaces */
    write32_v364(p,0xd0+8,3);
    write32_v364(p,0xd0+16,6);
    write32_v364(p,0xd0+24,16);
    write32_v364(p,0xf0+8,12);
    write32_v364(p,0xf0+12,3);
    write32_v364(p,0xf0+24,36);
    write32_v364(p,0xf0+28,16);
    write32_v364(p,0x110,1);
    write32_v364(p,0x110+12,0x120);
    write32_v364(p,0x120+8,2); /* Float3 */
    write16_v364(p,VERTICES_OFF_V364+0,0);
    write16_v364(p,VERTICES_OFF_V364+2,1);
    write16_v364(p,VERTICES_OFF_V364+4,2);
    for(unsigned i=0;i<36;++i)
        p[VERTICES_OFF_V364+16+i]=(unsigned char)(i*7u);
}
static void good_v364(void){
    unsigned char model[FILE_BYTES_V364];
    invented_flver_v364(model);
    ShytNativeFlver2AssetV363 asset={0};
    asset.flver=model;asset.flver_bytes=sizeof(model);
    ShytNativeGpuUploadCountsV364 counts={0};
    assert(shyt_native_flver2_gpu_requirements_v364(&asset,&counts));
    assert(counts.vertex_buffers==1 && counts.index_buffers==1 &&
           counts.draws==1 && counts.vertex_source_bytes==36 &&
           counts.index_source_bytes==6 && counts.staging_bytes_total==42);
    ShytNativeGpuVertexSpanV364 vertex[1]={0};
    ShytNativeGpuIndexSpanV364 index[1]={0};
    ShytNativeGpuDrawV364 draw[1]={0};
    assert(shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,1,index,1,draw,1,42,&counts));
    assert(vertex[0].source_offset==VERTICES_OFF_V364+16 &&
           vertex[0].bytes==36 && vertex[0].vertex_stride==12 &&
           vertex[0].vertex_count==3 && vertex[0].layout_index==0);
    assert(vertex[0].staging_offset==0 &&
           index[0].staging_offset==36);
    assert(index[0].source_offset==VERTICES_OFF_V364 &&
           index[0].bytes==6 && index[0].index_count==3 &&
           index[0].index_element_bytes==2 &&
           index[0].triangle_strip==1 && index[0].cull_backfaces==1);
    assert(draw[0].mesh_index==0 && draw[0].material_index==0 &&
           draw[0].face_set_index==0 && draw[0].vertex_count==3 &&
           draw[0].vertex_buffer_count==1 &&
           draw[0].vertex_buffer_indices[0]==0);
    unsigned char destination[48];
    memset(destination,0xAB,sizeof(destination));
    size_t written=999;
    assert(shyt_native_flver2_stage_bytes_v364(
        &asset,vertex[0].source_offset,vertex[0].bytes,
        destination,sizeof(destination),&written));
    assert(written==36 &&
           memcmp(destination,model+VERTICES_OFF_V364+16,36)==0);
    assert(destination[36]==0xAB);
    assert(shyt_native_flver2_stage_bytes_v364(
        &asset,index[0].source_offset,index[0].bytes,
        destination,sizeof(destination),&written));
    assert(written==6 &&
           memcmp(destination,model+VERTICES_OFF_V364,6)==0);
    /* Failed staging must not modify the destination or publish bytes. */
    unsigned char snapshot[48];
    memcpy(snapshot,destination,sizeof(snapshot));
    written=111;
    assert(!shyt_native_flver2_stage_bytes_v364(
        &asset,vertex[0].source_offset,vertex[0].bytes,
        destination,35,&written));
    assert(written==0 && memcmp(snapshot,destination,sizeof(snapshot))==0);
    written=111;
    assert(!shyt_native_flver2_stage_bytes_v364(
        &asset,UINT32_MAX,36,destination,sizeof(destination),&written));
    assert(written==0 && memcmp(snapshot,destination,sizeof(snapshot))==0);
    written=111;
    assert(!shyt_native_flver2_stage_bytes_v364(
        &asset,vertex[0].source_offset,vertex[0].bytes,
        model+0x40,sizeof(model)-0x40,&written));
    assert(written==0);
    assert(!shyt_native_flver2_stage_bytes_v364(
        &asset,vertex[0].source_offset,vertex[0].bytes,
        destination,sizeof(destination),NULL));
    /* No allocation or upload may exceed the caller's staging budget. */
    assert(!shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,1,index,1,draw,1,41,&counts));
    assert(counts.staging_bytes_total==0);
    /* Insufficient output arrays refuse before writing anything. */
    vertex[0].bytes=0xDEADBEEFu;
    counts.draws=999;
    assert(!shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,0,index,1,draw,1,42,&counts));
    assert(counts.draws==0 && vertex[0].bytes==0xDEADBEEFu);
    assert(!shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,1,index,0,draw,1,42,&counts));
    assert(!shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,1,index,1,draw,0,42,&counts));
    assert(!shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,1,index,1,draw,1,42,NULL));
    /* Revalidate after source mutation: old stats may not be trusted. */
    write16_v364(model,VERTICES_OFF_V364+4,99);
    counts.vertex_buffers=88;
    assert(!shyt_native_flver2_gpu_requirements_v364(&asset,&counts));
    assert(counts.vertex_buffers==0);
    assert(!shyt_native_flver2_gpu_plan_v364(
        &asset,vertex,1,index,1,draw,1,42,&counts));
    write16_v364(model,VERTICES_OFF_V364+4,2);
    assert(shyt_native_flver2_gpu_requirements_v364(&asset,&counts));
    asset.flver_bytes=FILE_BYTES_V364-1;
    assert(!shyt_native_flver2_gpu_requirements_v364(&asset,&counts));
}
static void empty_v364(void){
    unsigned char model[FILE_BYTES_V364];
    invented_flver_v364(model);
    write32_v364(model,24,0);
    write32_v364(model,32,0);
    write32_v364(model,36,0);
    write32_v364(model,0x50,0);
    write32_v364(model,0x54,0);
    write32_v364(model,12,0x80);
    write32_v364(model,16,0);
    ShytNativeFlver2AssetV363 asset={0};
    asset.flver=model;asset.flver_bytes=sizeof(model);
    ShytNativeGpuUploadCountsV364 counts={0};
    assert(shyt_native_flver2_gpu_requirements_v364(&asset,&counts));
    assert(counts.draws==0 && counts.vertex_buffers==0 &&
           counts.index_buffers==0);
    assert(shyt_native_flver2_gpu_plan_v364(
        &asset,NULL,0,NULL,0,NULL,0,0,&counts));
}
int main(void){
    good_v364();
    empty_v364();
    puts("NATIVE_V364_GPU_UPLOAD_PLAN_SYNTHETIC_PASS");
    return 0;
}
