/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "fios_fd_v639.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

unsigned char *bb_fios_open_v641(const char *, uint16_t, uintptr_t, void *(*)(size_t),
        int32_t (*)(const void *, int32_t *, const char *, const void *));
int32_t bb_fios_write_v640(unsigned char [static 17], const void *, int32_t,
        int64_t (*)(const void *, int32_t, const void *, int64_t),
        int32_t (*)(const void *, int32_t), void (*)(void));
int bb_fios_forward_sync_v638(const unsigned char [static 16], int32_t (*)(const void *, int32_t));
void bb_fios_close_v641(unsigned char [static 17], int32_t (*)(const void *, int32_t));
static struct bb_fd_table table = BB_FD_INIT;
static unsigned allocations, closes;
static int sync_result;

static void *allocate(size_t size) {
    assert(size == 24);
    void *p = malloc(size);
    assert(p);
    memset(p, 0xa5, size);
    ++allocations;
    return p;
}
/* Test adapter only. This proves 0x1a create/write and 0x0a write-only
 * reopen in this sandbox, not the complete Fios open-flag ABI. */
static int32_t open_fh(const void *a, int32_t *out, const char *p, const void *params) {
    assert(!a && *out == -1);
    const unsigned char *b = params;
    for (size_t i = 1; i < 24; ++i) assert(!b[i]);
    assert(b[0] == 0x1a || b[0] == 0x0a);
    int fd = open(p, O_WRONLY | O_CLOEXEC | (b[0] == 0x1a ? O_CREAT : 0), 0600);
    if (fd < 0) return -errno;
    int32_t id = bb_fd_adopt(&table, fd);
    if (id < 0) { assert(!close(fd)); return id; }
    *out = id;
    return 0;
}
static int64_t write_fh(const void *a, int32_t id, const void *p, int64_t n) {
    assert(!a && n >= 0);
    int fd = bb_fd_pin(&table, id);
    if (fd < 0) return fd;
    ssize_t r = write(fd, p, (size_t)n);
    int64_t rc = r < 0 ? -errno : r;
    assert(!close(fd));
    return rc;
}
static int32_t close_fh(const void *a, int32_t id) {
    assert(!a);
    ++closes;
    return bb_fd_close(&table, id);
}
static int32_t sync_fh(const void *a, int32_t id) {
    assert(!a);
    return sync_result = bb_fd_sync(&table, id);
}
static void report(void) { abort(); }

int main(void) {
    char dir[] = "/tmp/fios641-XXXXXX";
    assert(mkdtemp(dir) && !chdir(dir));
    assert(!bb_fios_open_v641("absent", 0x0a, 0, allocate, open_fh) && !allocations);
    static const int native_identity;
    uintptr_t identity = (uintptr_t)&native_identity, actual;
    unsigned char *o = bb_fios_open_v641("save", 0x1a, identity, allocate, open_fh);
    assert(o && allocations == 1 && o[16] == 1 && o[17] == 0xa5 && o[23] == 0xa5);
    memcpy(&actual, o, 8);
    uint32_t header;
    memcpy(&header, o + 8, 4);
    assert(actual == identity && header == UINT32_C(0xffff0001));
    assert(bb_fios_write_v640(o, "ABCD", 4, write_fh, close_fh, report) == 4);
    assert(bb_fios_forward_sync_v638(o, sync_fh) && !sync_result);
    int32_t id;
    memcpy(&id, o + 12, 4);
    o[16] = 0;
    bb_fios_close_v641(o, close_fh);
    assert(!closes && bb_fios_forward_sync_v638(o, sync_fh) && !sync_result);
    o[16] = 1;
    bb_fios_close_v641(o, close_fh);
    bb_fios_close_v641(o, close_fh);
    assert(closes == 1 && bb_fd_pin(&table, id) == -EBADF && !bb_fios_forward_sync_v638(o, sync_fh));
    free(o);
    o = bb_fios_open_v641("save", 0x0a, identity, allocate, open_fh);
    assert(o && allocations == 2);
    bb_fios_close_v641(o, close_fh);
    assert(closes == 2);
    free(o);
    char bytes[5];
    int fd = open("save", O_RDONLY | O_CLOEXEC);
    assert(fd >= 0 && read(fd, bytes, sizeof bytes) == 4 && !memcmp(bytes, "ABCD", 4));
    assert(!close(fd) && !unlink("save") && !chdir("/") && !rmdir(dir));
    assert(!pthread_mutex_destroy(&table.lock));
    return 0;
}
