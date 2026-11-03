/* SPDX-License-Identifier: GPL-2.0-or-later
 * FICTITIOUS DCX DFLT container matching the public BB/DS3 layout.
 * This is a header validation test, NOT a claimed game asset decoder.
 */
#include "native_dcx_dflt_header_v354.h"
#include "native_win_asset_fs_v351.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#endif
static void be32(unsigned char *p, unsigned n) {
    p[0]=(unsigned char)(n>>24);
    p[1]=(unsigned char)(n>>16);
    p[2]=(unsigned char)(n>>8);
    p[3]=(unsigned char)n;
}
static void fake(unsigned char h[76]) {
    memset(h,0,76);
    memcpy(h,"DCX\0",4);
    be32(h+4,0x10000);
    be32(h+8,0x18);
    be32(h+12,0x24);
    be32(h+16,0x44);
    be32(h+20,0x4c);
    memcpy(h+24,"DCS\0",4);
    be32(h+28,100);
    be32(h+32,32);
    memcpy(h+36,"DCP\0",4);
    memcpy(h+40,"DFLT",4);
    be32(h+44,0x20);
    h[48]=9;
    be32(h+64,0x10100);
    memcpy(h+68,"DCA\0",4);
    be32(h+72,8);
}
static void fail(unsigned char h[76],unsigned file_size) {
    ShytNativeDcxDfltHeaderV354 result;
    memset(&result,0x55,sizeof(result));
    assert(!shyt_native_dcx_dflt_probe_v354(h,76,file_size,&result));
    assert(result.compressed_bytes==0 && result.uncompressed_bytes==0 &&
           result.payload_offset==0 && result.compression_level==0);
}
int main(void) {
    unsigned char h[76];
    fake(h);
    ShytNativeDcxDfltHeaderV354 v={0};
    assert(shyt_native_dcx_dflt_probe_v354(h,76,108,&v));
    assert(v.uncompressed_bytes==100 && v.compressed_bytes==32 &&
           v.payload_offset==76 && v.compression_level==9);
    assert(!shyt_native_dcx_dflt_probe_v354(h,75,108,&v));
    fake(h);memcpy(h+40,"KRAK",4);fail(h,108);
    fake(h);h[0]='A';fail(h,108);
    fake(h);be32(h+16,0x24);fail(h,108);
    fake(h);be32(h+28,0);fail(h,108);
    fake(h);be32(h+28,0xFFFFFFFFu);fail(h,108);
    fake(h);be32(h+32,0xFFFFFFFFu);fail(h,108);
    fake(h);be32(h+32,1);fail(h,108);
    fake(h);be32(h+32,32);fail(h,76+31);
    fake(h);h[48]=0;fail(h,108);
    fake(h);h[52]=1;fail(h,108);
    fake(h);h[68]='Z';fail(h,108);
    fake(h);be32(h+4,0x11000);h[48]=8;
    assert(shyt_native_dcx_dflt_probe_v354(h,76,108,&v));
#ifdef _WIN32
    /* Also read the fictional DCX header through the genuine Win32
     * owner-owned game asset mount built in V351/V352, not fopen(). */
    wchar_t temp[4096], root[4096], path[4096];
    DWORD n=GetTempPathW(4096,temp);
    assert(n>0 && n<3900);
    assert(GetTempFileNameW(temp,L"dcx",0,root));
    assert(DeleteFileW(root) && CreateDirectoryW(root,0));
    int m=swprintf(path,4096,L"%ls\\asset.dcx",root);
    assert(m>0 && m<4096);
    HANDLE f=CreateFileW(path,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
    assert(f!=INVALID_HANDLE_VALUE);
    unsigned char dat[108]={0};
    fake(h);memcpy(dat,h,76);
    DWORD wrote=0;
    assert(WriteFile(f,dat,sizeof(dat),&wrote,NULL) && wrote==sizeof(dat));
    CloseHandle(f);
    ShytNativeWinAssetRootV351 mount={0};
    assert(shyt_native_win_asset_mount_v351(&mount,root));
    unsigned char header[76]={0};size_t got=0;
    assert(shyt_native_win_asset_read_at_v351(
        &mount,"/dvdroot_ps4/asset.dcx",0,header,76,&got) && got==76);
    assert(shyt_native_dcx_dflt_probe_v354(header,got,108,&v));
    assert(DeleteFileW(path) && RemoveDirectoryW(root));
#endif
    puts("SHYT_NATIVE_V354_BB_DS3_DCX_DEFLATE_HEADER_VALIDATION_PASS");
    return 0;
}
