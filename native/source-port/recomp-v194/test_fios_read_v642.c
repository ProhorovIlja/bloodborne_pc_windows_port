/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "fios_fd_v639.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int32_t bb_fios_read_v642(unsigned char [static 17], void *, int32_t,
        int64_t (*)(const void *, int32_t, void *, int64_t));
static struct bb_fd_table table = BB_FD_INIT;
static unsigned calls;

static int64_t read_fh(const void *attr, int32_t id, void *buf, int64_t n) {
    assert(!attr);
    ++calls;
    if (n < 0) return -EINVAL;
    int fd = bb_fd_pin(&table, id);
    if (fd < 0) return fd;
    ssize_t r;
    do { r = read(fd, buf, (size_t)n); } while (r < 0 && errno == EINTR);
    int64_t result = r < 0 ? -errno : r;
    assert(!close(fd));
    return result;
}

int main(void) {
    FILE *f = tmpfile();
    assert(f && write(fileno(f), "ABCD", 4) == 4);
    int fd = dup(fileno(f));
    assert(fd >= 0 && lseek(fd, 0, SEEK_SET) == 0);
    int32_t id = bb_fd_adopt(&table, fd), invalid = -1;
    assert(id > 0);
    unsigned char object[17] = {0}, buffer[8] = {0};
    object[16] = 1;
    memcpy(object + 12, &invalid, 4);
    assert(!bb_fios_read_v642(object, buffer, 8, read_fh) && !calls);
    memcpy(object + 12, &id, 4);
    assert(!bb_fios_read_v642(object, buffer, 0, read_fh) && !calls && object[16]);
    assert(bb_fios_read_v642(object, buffer, 8, read_fh) == 4);
    assert(calls == 1 && object[16] && !memcmp(buffer, "ABCD", 4));
    assert(!bb_fios_read_v642(object, buffer, 8, read_fh) && calls == 2 && !object[16]);
    int32_t after;
    memcpy(&after, object + 12, 4);
    assert(after == id && !bb_fd_close(&table, id));
    object[16] = 1;
    assert(bb_fios_read_v642(object, buffer, 8, read_fh) == -EBADF && !object[16]);
    assert(!fclose(f) && !pthread_mutex_destroy(&table.lock));
    puts("Fios read: short read, EOF, zero request and closed handle OK");
}
