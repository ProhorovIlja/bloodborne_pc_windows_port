/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int bb_fios_forward_sync_v638(const unsigned char [static 16],
                             int32_t (*)(const void *, int32_t));
static unsigned calls;
static int last_result;

static int32_t host_sync(const void *attr, int32_t fd) {
    assert(!attr);
    ++calls;
    last_result = fsync(fd);
    return last_result;
}

int main(void) {
    unsigned char object[16] = {0};
    int32_t handle = -1;
    memcpy(object + 12, &handle, sizeof handle);
    assert(!bb_fios_forward_sync_v638(object, host_sync) && calls == 0);
    FILE *f = tmpfile();
    assert(f && write(fileno(f), "sync", 4) == 4);
    handle = fileno(f);
    memcpy(object + 12, &handle, sizeof handle);
    assert(!bb_fios_forward_sync_v638(object, NULL) && calls == 0);
    assert(bb_fios_forward_sync_v638(object, host_sync) && calls == 1 && last_result == 0);
    assert(!fclose(f));
    assert(bb_fios_forward_sync_v638(object, host_sync) && calls == 2 && last_result == -1);
    puts("Fios2 sync: negative, unbound, host fsync, closed descriptor OK");
}
