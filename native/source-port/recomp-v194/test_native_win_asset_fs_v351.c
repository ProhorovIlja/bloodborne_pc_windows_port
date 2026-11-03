/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real Windows API test on invented, non-retail game-like directory/files.
 */
#include "native_win_asset_fs_v351.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static void append(wchar_t out[1024],const wchar_t *a,const wchar_t *b) {
    size_t n=wcslen(a), m=wcslen(b);
    assert(n+m+2<1024);
    wmemcpy(out,a,n);
    out[n]=L'\\';
    wmemcpy(out+n+1,b,m+1);
}

int main(void) {
    wchar_t temp[1024], sandbox[1024], game[1024], map[1024];
    wchar_t file[1024], outside[1024], linked[1024], hardlink[1024];
    DWORD count=GetTempPathW(1024,temp);
    assert(count && count<1000);
    assert(GetTempFileNameW(temp,L"v35",0,sandbox)!=0);
    assert(DeleteFileW(sandbox));
    assert(CreateDirectoryW(sandbox,NULL));
    append(game,sandbox,L"dvdroot_ps4");
    assert(CreateDirectoryW(game,NULL));
    append(map,game,L"map");
    assert(CreateDirectoryW(map,NULL));
    append(file,map,L"m24_01_00_00.msb.dcx");
    const char fake[]="DCX\0FAKE-MAP";
    HANDLE h=CreateFileW(file,GENERIC_WRITE,0,NULL,CREATE_NEW,
                         FILE_ATTRIBUTE_NORMAL,NULL);
    assert(h!=INVALID_HANDLE_VALUE);
    DWORD bytes=0;
    assert(WriteFile(h,fake,(DWORD)sizeof(fake),&bytes,NULL));
    assert(bytes==sizeof(fake));
    CloseHandle(h);
    append(outside,sandbox,L"external.txt");
    h=CreateFileW(outside,GENERIC_WRITE,0,NULL,CREATE_NEW,
                  FILE_ATTRIBUTE_NORMAL,NULL);
    assert(h!=INVALID_HANDLE_VALUE);
    assert(WriteFile(h,"PRIVATE",7,&bytes,NULL));
    CloseHandle(h);
    ShytNativeWinAssetRootV351 root={0};
    assert(shyt_native_win_asset_mount_v351(&root,game));
    assert(root.mounted && root.prefix_chars>4);
    const char *good="/dvdroot_ps4/map/m24_01_00_00.msb.dcx";
    char buffer[32];
    memset(buffer,0xcc,sizeof(buffer));
    size_t got=99;
    assert(shyt_native_win_asset_read_at_v351(&root,good,0,buffer,4,&got));
    assert(got==4 && memcmp(buffer,"DCX\0",4)==0);
    assert(shyt_native_win_asset_read_at_v351(&root,good,4,buffer,4,&got));
    assert(got==4 && memcmp(buffer,"FAKE",4)==0);
    assert(shyt_native_win_asset_read_at_v351(&root,good,9999,buffer,4,&got));
    assert(got==0);
    const char *bad[]={
        "/dvdroot_ps4/../external.txt",
        "/dvdroot_ps4/map/../../external.txt",
        "C:\\external.txt",
        "\\\\server\\share\\file",
        "/dvdroot_ps4/map/CON.txt",
        "/dvdroot_ps4/map/NUL",
        "/dvdroot_ps4/map//file.dcx",
        "/dvdroot_ps4/map/trailing.",
        "/dvdroot_ps4/map\\other",
        "/dvdroot_ps4/map/file:alt",
        "/dvdroot_ps4/%2E%2E/external.txt",
        "/dvdroot_ps4/",
        "/app0/map/m24_01_00_00.msb.dcx",
        "/dvdroot_ps4/map/not-here.dcx"
    };
    for (size_t i=0;i<sizeof(bad)/sizeof(bad[0]);++i) {
        got=19;
        assert(!shyt_native_win_asset_read_at_v351(&root,bad[i],0,buffer,4,&got));
        assert(got==0);
    }
    got=90;
    assert(!shyt_native_win_asset_read_at_v351(&root,good,0,buffer,
                                               SHYT_WIN_ASSET_MAX_READ_V351+1,&got));
    assert(got==0);
    got=50;
    assert(!shyt_native_win_asset_read_at_v351(&root,good,UINT64_MAX,buffer,4,&got));
    assert(got==0);
    append(hardlink,map,L"external-hardlink.dcx");
    if (CreateHardLinkW(hardlink,outside,NULL)) {
        got=72;
        assert(!shyt_native_win_asset_read_at_v351(
            &root,"/dvdroot_ps4/map/external-hardlink.dcx",0,buffer,4,&got));
        assert(got==0);
        assert(DeleteFileW(hardlink));
    }
    append(linked,map,L"external-link.dcx");
    if (CreateSymbolicLinkW(linked,outside,0x2)) {
        got=73;
        assert(!shyt_native_win_asset_read_at_v351(
            &root,"/dvdroot_ps4/map/external-link.dcx",0,buffer,4,&got));
        assert(got==0);
        assert(DeleteFileW(linked));
    }
    assert(DeleteFileW(file));
    assert(DeleteFileW(outside));
    assert(RemoveDirectoryW(map));
    assert(RemoveDirectoryW(game));
    assert(RemoveDirectoryW(sandbox));
    puts("SHYT_NATIVE_V351_WIN32_REAL_FILE_IO_FAKE_DVDROOT_NO_EBOOT_PASS");
    return 0;
}
#else
int main(void) {
    ShytNativeWinAssetRootV351 root={0};
    size_t got=17;
    assert(!shyt_native_win_asset_mount_v351(&root,L"/missing"));
    assert(!shyt_native_win_asset_read_at_v351(
        &root,"/dvdroot_ps4/map/a.dcx",0,&root,1,&got));
    assert(got==0);
    puts("SHYT_NATIVE_V351_WINDOWS_ONLY_NO_POSIX_SHIM_PASS");
    return 0;
}
#endif
