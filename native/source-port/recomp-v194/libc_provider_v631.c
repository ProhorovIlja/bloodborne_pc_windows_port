/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "libc_strncmp_v629.c"
#include "libc_wide_v630.c"

/* Native call sites must select the matching union member. This is a provider
 * for recompiled/source code, not a PS4 PLT or a generic ABI trampoline. */
#define BB_LIBC_SIGNATURES631(X) \
    X(copy,void *,void *,const void *,size_t) \
    X(fill,void *,void *,int,size_t) \
    X(memcmp,int,const void *,const void *,size_t) \
    X(memchr,void *,const void *,int,size_t) \
    X(len,size_t,const char *) \
    X(cmp,int,const char *,const char *) \
    X(ncmp,int,const char *,const char *,size_t) \
    X(chr,char *,const char *,int) \
    X(find,char *,const char *,const char *) \
    X(strcpy,char *,char *,const char *) \
    X(ncopy,char *,char *,const char *,size_t) \
    X(span,size_t,const char *,const char *) \
    X(wlen,size_t,const uint16_t *) \
    X(wcmp,int,const uint16_t *,const uint16_t *) \
    X(wncmp,int,const uint16_t *,const uint16_t *,size_t) \
    X(wchr,const uint16_t *,const uint16_t *,uint16_t,size_t)
#define BB_ENUM631(name,ret,...) BB_LIBC631_##name,
typedef enum { BB_LIBC_SIGNATURES631(BB_ENUM631) } BbLibcSignature631;
#undef BB_ENUM631
#define BB_MEMBER631(name,ret,...) ret (*name)(__VA_ARGS__);
typedef union { BB_LIBC_SIGNATURES631(BB_MEMBER631) } BbLibcTarget631;
#undef BB_MEMBER631
#undef BB_LIBC_SIGNATURES631

typedef struct { const char *nid; BbLibcSignature631 signature; BbLibcTarget631 target; } BbLibcRoute631;
#define BB_ROUTE631(nid,sig,fn) {nid,BB_LIBC631_##sig,{.sig=fn}}
static const BbLibcRoute631 routes631[]={
    BB_ROUTE631("Q3VBxCXhUHs",copy,memcpy),
    BB_ROUTE631("+P6FRGH4LfA",copy,memmove),
    BB_ROUTE631("8zTFvBIAIN8",fill,memset),
    BB_ROUTE631("DfivPArhucg",memcmp,memcmp),
    BB_ROUTE631("j4ViWNHEgww",len,strlen),
    BB_ROUTE631("Ovb2dSJOAuE",cmp,strcmp),
    BB_ROUTE631("aesyjrHVWy4",ncmp,bb_libc_strncmp_v629),
    BB_ROUTE631("ob5xAW4ln-0",chr,strchr),
    BB_ROUTE631("viiwFMaNamA",find,strstr),
    BB_ROUTE631("8u8lPzUEq+U",memchr,memchr),
    BB_ROUTE631("9yDWMxEFdJU",chr,strrchr),
    BB_ROUTE631("kiZSXIWd9vg",strcpy,strcpy),
    BB_ROUTE631("6sJWiWSRuqk",ncopy,strncpy),
    BB_ROUTE631("Ls4tzzhimqQ",strcpy,strcat),
    BB_ROUTE631("kHg45qPC6f0",ncopy,strncat),
    BB_ROUTE631("kDZvoVssCgQ",find,strpbrk),
    BB_ROUTE631("-kU6bB4M-+k",span,strspn),
    BB_ROUTE631("q0F6yS-rCms",span,strcspn),
    BB_ROUTE631("WkkeywLJcgU",wlen,bb_libc_wcslen_v630),
    BB_ROUTE631("pNtJdE3x49E",wcmp,bb_libc_wcscmp_v630),
    BB_ROUTE631("E8wCoUEbfzk",wncmp,bb_libc_wcsncmp_v630),
    BB_ROUTE631("fnUEjBCNRVU",wchr,bb_libc_wmemchr_v630),
    BB_ROUTE631("QJ5xVfKkni0",wncmp,bb_libc_wmemcmp_v630),
};
#undef BB_ROUTE631

/* Versions are the decoded PS4 namespace fields, not host libc versions.
 * Object imports, unknown functions and wrong signatures never bind. */
const BbLibcRoute631 *bb_libc_resolve_v631(const char *nid,const char *module,
    unsigned module_version,const char *library,unsigned library_version,
    unsigned elf_type,BbLibcSignature631 signature) {
    if (!nid || !module || !library || module_version!=0x101 || library_version!=1 ||
        elf_type!=2 || strcmp(module,"libc") || strcmp(library,"libc")) return NULL;
    for (size_t i=0;i<sizeof routes631/sizeof *routes631;++i) {
        const BbLibcRoute631 *r=routes631+i;
        if (signature==r->signature && !strcmp(nid,r->nid)) return r;
    }
    return NULL;
}
