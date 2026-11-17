/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "fios_fd_v639.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int32_t bb_fios_write_v640(unsigned char [static 17], const void *, int32_t,
        int64_t (*)(const void *, int32_t, const void *, int64_t),
        int32_t (*)(const void *, int32_t), void (*)(void));
int bb_fios_forward_sync_v638(const unsigned char [static 16], int32_t (*)(const void *, int32_t));
static struct bb_fd_table table = BB_FD_INIT;
static unsigned writes, closes, reports;
static int sync_result;

static int64_t write_fh(const void *a, int32_t id, const void *p, int64_t n) {
    assert(!a);
    ++writes;
    if (n < 0) return -EINVAL;
    int fd = bb_fd_pin(&table, id);
    if (fd < 0) return fd;
    ssize_t r;
    do { r = write(fd, p, (size_t)n); } while (r < 0 && errno == EINTR);
    int64_t result = r < 0 ? -errno : r;
    assert(!close(fd));
    return result;
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
static void report(void) { ++reports; }

int main(void) {
    FILE *f = tmpfile();
    assert(f);
    int fd = dup(fileno(f));
    assert(fd >= 0);
    int32_t id = bb_fd_adopt(&table, fd), current;
    assert(id > 0);
    unsigned char o[17] = {0};
    memcpy(o + 12, &id, 4);
    assert(bb_fios_write_v640(o, "data", 4, write_fh, close_fh, report) == 4);
    assert(bb_fios_forward_sync_v638(o, sync_fh) && sync_result == 0);
    assert(bb_fios_write_v640(o, "", -1, write_fh, close_fh, report) == -EINVAL);
    assert(closes == 0);
    o[16] = 1;
    assert(bb_fios_write_v640(o, "", 0, write_fh, close_fh, report) == 0);
    memcpy(&current, o + 12, 4);
    assert(current == -1 && closes == 1 && bb_fd_pin(&table, id) == -EBADF);
    assert(!bb_fios_forward_sync_v638(o, sync_fh));
    assert(bb_fios_write_v640(o, "!", 1, write_fh, close_fh, report) == 0);
    assert(writes == 3 && reports == 0);
    char buf[5];
    assert(pread(fileno(f), buf, sizeof buf, 0) == 4 && !memcmp(buf, "data", 4));
    assert(!fclose(f) && !pthread_mutex_destroy(&table.lock));
    puts("Fios write/sync/conditional-close: OK");
}
