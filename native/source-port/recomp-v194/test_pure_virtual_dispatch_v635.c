/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "pure_virtual_dispatch_v635.h"
#include "libc_pure_virtual_v633.c"
#include <assert.h>
#include <inttypes.h>
#include <signal.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

static unsigned calls;
static void probe(void) { ++calls; }

int main(int argc, char **argv) {
    enum { limit = 4096 };
    static struct bb_v634_reloc rows[limit];
    static struct bb_v634_slot table[limit];
    size_t n = 0;
    if (argc == 2 && !strcmp(argv[1], "--stdin")) {
        uint64_t slot;
        int status;
        while ((status = scanf("%" SCNu64, &slot)) == 1) {
            if (n == limit) return 2;
            rows[n++] = (struct bb_v634_reloc){slot,1,0};
        }
        if (status != EOF || ferror(stdin) || !n) return 2;
    } else if (argc == 1) {
        n = 3;
        for (size_t i = 0; i < n; ++i)
            rows[i] = (struct bb_v634_reloc){16*i+8,1,0};
    } else return 2;
    assert(bb_v634_build(rows,n,UINT64_MAX,probe,table,limit));
    for (size_t i = 0; i < n; ++i) {
        assert(bb_v635_dispatch(table,n,rows[i].offset) == BB_V635_TARGET_RETURNED);
        assert(bb_v635_dispatch(table,n,rows[i].offset+1) == BB_V635_UNRESOLVED);
    }
    assert(calls == n);
    assert(bb_v635_dispatch(NULL,n,rows[0].offset) == BB_V635_UNRESOLVED);
    BbV634Target fatal = bb_libc_pure_virtual_resolve_v633("zr094EQ39Ww","libc",257,"libc",1,2);
    assert(bb_v634_build(rows,n,UINT64_MAX,fatal,table,limit));
    const struct rlimit no_core = {0,0};
    assert(!setrlimit(RLIMIT_CORE,&no_core));
    const size_t points[] = {0,n/2,n-1};
    for (size_t i = 0; i < sizeof points/sizeof *points; ++i) {
        pid_t child = fork();
        if (child < 0) return 2;
        if (!child) {
            (void)bb_v635_dispatch(table,n,rows[points[i]].offset);
            _exit(3);
        }
        int status;
        assert(waitpid(child,&status,0) == child);
        assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT);
    }
    printf("slots=%zu hits=%u misses=%zu fatal=3\n",n,calls,n+1);
    return 0;
}
