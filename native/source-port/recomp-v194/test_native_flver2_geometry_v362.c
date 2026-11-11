/* SPDX-License-Identifier: GPL-2.0-or-later
 * Invented FLVER2 geometry records: no original game bytes used.
 */
#include "native_flver2_geometry_v362.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define FILE_SIZE_V362 0x1b4u
#define DATA_OFF_V362 0x180u
static void w16(unsigned char *b, unsigned p, uint16_t n){b[p]=(unsigned char)n;b[p+1]=(unsigned char)(n>>8);}
static void w32(unsigned char *b, unsigned p, uint32_t n){w16(b,p,(uint16_t)n);w16(b,p+2,(uint16_t)(n>>16));}
static void invented(unsigned char *b) {
    memset(b,0,FILE_SIZE_V362);
    memcpy(b,"FLVER\0L\0",8);
    w32(b,8,0x20014u);
    w32(b,12,DATA_OFF_V362);
    w32(b,16,52u); /* six index bytes + padding + 36 vertex bytes */
    w32(b,24,1u); /* material */
    w32(b,32,1u); /* mesh */
    w32(b,36,1u); /* vertex buffer */
    b[0x49]=1; /* UTF16 */
    w32(b,0x50,1u); /* face set */
    w32(b,0x54,1u); /* layout */
    /* material record at 0x80, followed by mesh at 0xA0 */
    b[0xA0]=1; /* dynamic */
    w32(b,0xA0+16,0xffffffffu); /* bone -1 */
    w32(b,0xA0+32,1u); /* face count */
    w32(b,0xA0+36,0x138u); /* face index refs */
    w32(b,0xA0+40,1u); /* VB count */
    w32(b,0xA0+44,0x13cu); /* VB index refs */
    /* face set record at 0xD0 */
    w32(b,0xD0+8,3u);
    w32(b,0xD0+16,6u);
    w32(b,0xD0+24,16u);
    /* VB record at 0xF0 */
    w32(b,0xF0+8,12u); /* stride */
    w32(b,0xF0+12,3u); /* vertices */
    w32(b,0xF0+24,36u); /* size */
    w32(b,0xF0+28,16u); /* rel offset */
    /* layout record at 0x110; member starts 0x120 */
    w32(b,0x110,1u);
    w32(b,0x110+12,0x120u);
    w32(b,0x120+8,2u); /* Float3, 12 bytes */
    /* face + VB reference indices are both 0 */
    w16(b,DATA_OFF_V362+0,0u);
    w16(b,DATA_OFF_V362+2,1u);
    w16(b,DATA_OFF_V362+4,2u);
    for (unsigned j=0;j<36;++j) b[DATA_OFF_V362+16+j]=(unsigned char)(j*7u);
}
static void refused(unsigned char *b, size_t size) {
    ShytNativeFlver2GeometryV362 parsed={0};
    parsed.mesh_count=999;
    assert(!shyt_native_flver2_geometry_probe_v362(b,size,&parsed));
    assert(parsed.mesh_count==0 && parsed.validated_vertex_bytes==0u);
}
static void accepted(unsigned char *b,size_t size) {
    ShytNativeFlver2GeometryV362 parsed={0};
    assert(shyt_native_flver2_geometry_probe_v362(b,size,&parsed));
    assert(parsed.version==0x20014 && parsed.data_offset==DATA_OFF_V362);
    assert(parsed.material_count==1 && parsed.mesh_count==1 &&
           parsed.vertex_buffer_count==1 && parsed.face_set_count==1 &&
           parsed.layout_count==1);
    assert(parsed.total_vertices==3 && parsed.total_index_elements==3 &&
           parsed.validated_vertex_bytes==36 && parsed.validated_index_bytes==6);
}
int main(void){
    unsigned char b[FILE_SIZE_V362];
    invented(b);accepted(b,sizeof(b));
    refused(b,0x7fu);
    refused(b,sizeof(b)-1);
    b[0]='Z';refused(b,sizeof(b));b[0]='F';
    b[6]='B';refused(b,sizeof(b));b[6]='L';
    w32(b,8,0x20015u);refused(b,sizeof(b));w32(b,8,0x20014u);
    w32(b,12,0x10000000u);refused(b,sizeof(b));w32(b,12,DATA_OFF_V362);
    w32(b,0x50,0xffffffffu);refused(b,sizeof(b));w32(b,0x50,1u);
    b[0x49]=0;refused(b,sizeof(b));b[0x49]=1;
    w32(b,0xD0+8,4);refused(b,sizeof(b));w32(b,0xD0+8,3);
    w32(b,0xD0+16,8);refused(b,sizeof(b));w32(b,0xD0+16,6);
    w32(b,0xD0+24,8);refused(b,sizeof(b));w32(b,0xD0+24,16);
    w32(b,0xD0+0,0x40000000u);refused(b,sizeof(b));w32(b,0xD0,0);
    w32(b,0xF0+8,16u);refused(b,sizeof(b));w32(b,0xF0+8,12u);
    w32(b,0xF0+24,100u);refused(b,sizeof(b));w32(b,0xF0+24,36u);
    w32(b,0xF0+28,0x10000u);refused(b,sizeof(b));w32(b,0xF0+28,16u);
    w32(b,0xF0+4,1u);refused(b,sizeof(b));w32(b,0xF0+4,0u);
    w32(b,0x110+12,DATA_OFF_V362);refused(b,sizeof(b));w32(b,0x110+12,0x120u);
    w32(b,0x120+8,0xF0u);refused(b,sizeof(b));w32(b,0x120+8,2u);
    w32(b,0x120+4,1u);refused(b,sizeof(b));w32(b,0x120+4,0u);
    w32(b,0xA0+4,1u);refused(b,sizeof(b));w32(b,0xA0+4,0u);
    w32(b,0xA0+16,500u);refused(b,sizeof(b));w32(b,0xA0+16,0xFFFFFFFFu);
    w32(b,0xA0+36,DATA_OFF_V362);refused(b,sizeof(b));w32(b,0xA0+36,0x138u);
    w32(b,0xA0+44,DATA_OFF_V362);refused(b,sizeof(b));w32(b,0xA0+44,0x13cu);
    w32(b,0x138,2);refused(b,sizeof(b));w32(b,0x138,0);
    w32(b,0x13c,2);refused(b,sizeof(b));w32(b,0x13c,0);
    w16(b,DATA_OFF_V362+4,8);refused(b,sizeof(b));w16(b,DATA_OFF_V362+4,2);
    accepted(b,sizeof(b));
    /* Bone-only model with zero geometry is valid in actual CUSA03173. */
    invented(b);
    w32(b,24,0); w32(b,32,0); w32(b,36,0);
    w32(b,0x50,0);w32(b,0x54,0);
    w32(b,12,0x80u);w32(b,16,0);
    /* zero faces/VBs; other metadata bytes are not interpreted */
    ShytNativeFlver2GeometryV362 empty={0};
    assert(shyt_native_flver2_geometry_probe_v362(b,FILE_SIZE_V362,&empty));
    assert(empty.mesh_count==0 && empty.total_vertices==0);
    puts("NATIVE_V362_SYNTHETIC_FLVER2_GEOMETRY_BOUNDS_PASS");
    return 0;
}
