/* SPDX-License-Identifier: GPL-2.0-or-later
 * Windows-native, read-only asset IO. No PS4 compat runtime or guest ELF.
 * Proprietary files remain strictly on the owner's disk.
 */
#include "native_win_asset_fs_v351.h"
#include <limits.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <wctype.h>

static int ascii_component_ok_v351(const char *component, size_t len) {
    if (!len || len > 255 || component[0] == '.' ||
        component[len-1] == '.' || component[len-1] == ' ')
        return 0;
    for (size_t i=0;i<len;i++) {
        unsigned char c=(unsigned char)component[i];
        if (!((c>='A' && c<='Z') || (c>='a' && c<='z') ||
              (c>='0' && c<='9') || c=='_' || c=='-' || c=='.'))
            return 0;
    }
    /* Windows names are devices even when followed by an extension.
     * Do not let a game path accidentally read device streams. */
    char upper[8]={0};
    size_t first=0;
    while(first<len && first<7 && component[first]!='.') {
        char c=component[first];
        upper[first]=(c>='a' && c<='z') ? (char)(c-'a'+'A') : c;
        ++first;
    }
    upper[first]=0;
    if (!strcmp(upper,"CON") || !strcmp(upper,"NUL") ||
        !strcmp(upper,"PRN") || !strcmp(upper,"AUX") ||
        (first==4 && (!memcmp(upper,"COM",3) ||
                      !memcmp(upper,"LPT",3)) &&
         upper[3]>='1' && upper[3]<='9'))
        return 0;
    return 1;
}

static int logical_asset_path_v351(const ShytNativeWinAssetRootV351 *root,
                                   const char *logical, wchar_t out[SHYT_WIN_ASSET_PATH_CAP_V351]) {
    static const char prefix[]="/dvdroot_ps4/";
    const size_t magic_len=sizeof(prefix)-1;
    if (!root || !root->mounted || !logical ||
        strncmp(logical,prefix,magic_len)!=0)
        return 0;
    size_t i=magic_len, j=root->prefix_chars;
    if (!j || j >= SHYT_WIN_ASSET_PATH_CAP_V351 ||
        root->canonical_prefix[j-1]!=L'\\')
        return 0;
    wmemcpy(out,root->canonical_prefix,j);
    const size_t start=i;
    while(logical[i]) {
        const size_t begin=i;
        while (logical[i] && logical[i]!='/') ++i;
        const size_t part=i-begin;
        if (!ascii_component_ok_v351(logical+begin,part))
            return 0;
        if (j+part+2 >= SHYT_WIN_ASSET_PATH_CAP_V351)
            return 0;
        for(size_t n=0;n<part;++n)
            out[j++]=(wchar_t)(unsigned char)logical[begin+n];
        if (!logical[i]) break;
        ++i;
        if (!logical[i]) return 0;
        out[j++]=L'\\';
    }
    if (i==start) return 0;
    out[j]=0;
    return 1;
}

static int root_prefix_v351(HANDLE handle,wchar_t *out,size_t cap,size_t *n) {
    DWORD count;
    if (!n || cap<4 || cap>UINT32_MAX)
        return 0;
    count=GetFinalPathNameByHandleW(handle,out,(DWORD)(cap-2),FILE_NAME_NORMALIZED);
    if (!count || count>=cap-2) return 0;
    if (out[count-1]!=L'\\') out[count++]=L'\\';
    out[count]=0;
    *n=(size_t)count;
    return 1;
}

int shyt_native_win_asset_mount_v351(ShytNativeWinAssetRootV351 *root,
                                     const wchar_t *root_dir) {
    if (!root) return 0;
    memset(root,0,sizeof(*root));
    if (!root_dir || !root_dir[0]) return 0;
    DWORD attr=GetFileAttributesW(root_dir);
    if (attr==INVALID_FILE_ATTRIBUTES || (attr&FILE_ATTRIBUTE_DIRECTORY)==0 ||
        (attr&FILE_ATTRIBUTE_REPARSE_POINT)!=0) return 0;
    HANDLE h=CreateFileW(root_dir,FILE_READ_ATTRIBUTES,
                          FILE_SHARE_READ,0,OPEN_EXISTING,
                          FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,0);
    if (h==INVALID_HANDLE_VALUE) return 0;
    size_t n=0;
    const int ok=root_prefix_v351(h,root->canonical_prefix,
                                  SHYT_WIN_ASSET_PATH_CAP_V351,&n);
    CloseHandle(h);
    if (!ok) { memset(root,0,sizeof(*root)); return 0; }
    root->prefix_chars=n;
    root->mounted=1;
    return 1;
}

int shyt_native_win_asset_read_at_v351(
    const ShytNativeWinAssetRootV351 *root,const char *logical_path,
    uint64_t offset,void *out,size_t max_bytes,size_t *got) {
    if (!got) return 0;
    *got=0;
    /* V352: one security gate for both short single-shot reads and
     * persistent streaming handles. Avoid duplicated containment checks
     * silently diverging as the native asset API grows. */
    ShytNativeWinAssetStreamV352 stream={0};
    if (!shyt_native_win_asset_stream_open_v352(root,logical_path,&stream))
        return 0;
    const int ok=shyt_native_win_asset_stream_read_v352(
        &stream,offset,out,max_bytes,got);
    shyt_native_win_asset_stream_close_v352(&stream);
    return ok;
}

int shyt_native_win_asset_stream_open_v352(
    const ShytNativeWinAssetRootV351 *root,const char *logical_path,
    ShytNativeWinAssetStreamV352 *stream) {
    if (!stream || stream->open || stream->native_handle) return 0;
    wchar_t path[SHYT_WIN_ASSET_PATH_CAP_V351];
    if (!logical_asset_path_v351(root,logical_path,path)) return 0;
    HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,0,OPEN_EXISTING,
                         FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_OVERLAPPED,0);
    if (h==INVALID_HANDLE_VALUE) return 0;
    BY_HANDLE_FILE_INFORMATION info;
    wchar_t final[SHYT_WIN_ASSET_PATH_CAP_V351];
    const DWORD len=GetFinalPathNameByHandleW(
        h,final,SHYT_WIN_ASSET_PATH_CAP_V351,FILE_NAME_NORMALIZED);
    LARGE_INTEGER size;
    if (!GetFileInformationByHandle(h,&info) ||
        (info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY)) ||
        info.nNumberOfLinks!=1 ||
        !len || len>=SHYT_WIN_ASSET_PATH_CAP_V351 ||
        len<=root->prefix_chars ||
        _wcsnicmp(final,root->canonical_prefix,root->prefix_chars)!=0 ||
        !GetFileSizeEx(h,&size) || size.QuadPart<0) {
        CloseHandle(h);
        return 0;
    }
    stream->native_handle=(void*)h;
    stream->file_size=(uint64_t)size.QuadPart;
    stream->open=1;
    return 1;
}

int shyt_native_win_asset_stream_read_v352(
    const ShytNativeWinAssetStreamV352 *stream,
    uint64_t offset,void *out,size_t max_bytes,size_t *got) {
    if (!got) return 0;
    *got=0;
    if (!stream || !stream->open || !stream->native_handle ||
        !out || !max_bytes || max_bytes>SHYT_WIN_ASSET_MAX_READ_V351 ||
        offset>INT64_MAX) return 0;
    if (offset>=stream->file_size) return 1;
    const uint64_t left=stream->file_size-offset;
    const DWORD take=(DWORD)(left<max_bytes ? left : max_bytes);
    OVERLAPPED operation;
    memset(&operation,0,sizeof(operation));
    operation.Offset=(DWORD)offset;
    operation.OffsetHigh=(DWORD)(offset>>32);
    /* V353: with concurrent OVERLAPPED reads on one native handle,
     * waiting on the shared FILE HANDLE cannot identify one operation's
     * completion. Win32 requires a separate manual-reset event per
     * in-flight operation. Keep stack OVERLAPPED alive until completion;
     * don't accidentally close it while kernel IO still owns the pointer.
     */
    operation.hEvent=CreateEventW(NULL,TRUE,FALSE,NULL);
    if (!operation.hEvent) return 0;
    HANDLE h=(HANDLE)stream->native_handle;
    const BOOL started=ReadFile(h,out,take,NULL,&operation);
    DWORD transferred=0;
    if (!started) {
        const DWORD error=GetLastError();
        if (error==ERROR_HANDLE_EOF) {
            CloseHandle(operation.hEvent);
            return 1;
        }
        if (error!=ERROR_IO_PENDING) {
            CloseHandle(operation.hEvent);
            return 0;
        }
    }
    const BOOL finished=GetOverlappedResult(h,&operation,&transferred,TRUE);
    CloseHandle(operation.hEvent);
    if (!finished || transferred>take) return 0;
    *got=(size_t)transferred;
    return 1;
}

void shyt_native_win_asset_stream_close_v352(
    ShytNativeWinAssetStreamV352 *stream) {
    if (!stream) return;
    if (stream->open && stream->native_handle)
        CloseHandle((HANDLE)stream->native_handle);
    stream->native_handle=NULL;
    stream->file_size=0;
    stream->open=0;
}

#else
/* Non-Windows builds may link headers to type-check their callers.
 * The native file handler never silently uses POSIX as a PS4 runtime. */
int shyt_native_win_asset_stream_open_v352(
    const ShytNativeWinAssetRootV351 *root,const char *logical_path,
    ShytNativeWinAssetStreamV352 *stream) {
    (void)root;(void)logical_path;
    if (stream) memset(stream,0,sizeof(*stream));
    return 0;
}
int shyt_native_win_asset_stream_read_v352(
    const ShytNativeWinAssetStreamV352 *stream,
    uint64_t offset,void *out,size_t max_bytes,size_t *got) {
    (void)stream;(void)offset;(void)out;(void)max_bytes;
    if (got) *got=0;
    return 0;
}
void shyt_native_win_asset_stream_close_v352(
    ShytNativeWinAssetStreamV352 *stream) {
    if (stream) memset(stream,0,sizeof(*stream));
}
int shyt_native_win_asset_mount_v351(ShytNativeWinAssetRootV351 *root,
                                     const wchar_t *root_dir) {
    (void)root;(void)root_dir;
    return 0;
}
int shyt_native_win_asset_read_at_v351(
    const ShytNativeWinAssetRootV351 *root,const char *logical_path,
    uint64_t offset,void *out,size_t max_bytes,size_t *got) {
    (void)root;(void)logical_path;(void)offset;(void)out;(void)max_bytes;
    if (got) *got=0;
    return 0;
}
#endif
