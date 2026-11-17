/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "libc_pure_virtual_v633.c"
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#include <sys/resource.h>

int main(void) {
    const char *nid = "zr094EQ39Ww";
    BbPureVirtualTarget633 route = bb_libc_pure_virtual_resolve_v633(nid, "libc", 257, "libc", 1, 2);
    if (!route || bb_libc_pure_virtual_resolve_v633(nid, "libc", 256, "libc", 1, 2) ||
        bb_libc_pure_virtual_resolve_v633(nid, "libc", 257, "libc", 2, 2) ||
        bb_libc_pure_virtual_resolve_v633(nid, "libc", 257, "libc", 1, 1) ||
        bb_libc_pure_virtual_resolve_v633(nid, "libc", 257, "other", 1, 2) ||
        bb_libc_pure_virtual_resolve_v633(nid, "other", 257, "libc", 1, 2) ||
        bb_libc_pure_virtual_resolve_v633("unknown", "libc", 257, "libc", 1, 2)) return 1;
    const struct rlimit no_core = {0, 0};
    if (setrlimit(RLIMIT_CORE, &no_core)) return 2;
    pid_t child = fork();
    if (child < 0) return 2;
    if (child == 0) {
        route();
        _exit(3);
    }
    int status;
    if (waitpid(child, &status, 0) != child) return 2;
    return !(WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT);
}
