/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "fios_fd_v639.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int bb_fios_forward_sync_v638(const unsigned char [static 16],
                             int32_t (*)(const void *, int32_t));
static struct bb_fd_table table = BB_FD_INIT;
static int result;

static int32_t sync_cb(const void *attr, int32_t id) {
    assert(!attr);
    return result = bb_fd_sync(&table, id);
}

static void *close_worker(void *p) {
    assert(bb_fd_close(&table, *(int32_t *)p) == 0);
    return NULL;
}

int main(void) {
    FILE *a = tmpfile(), *b = tmpfile();
    assert(a && b);
    int original = dup(fileno(a));
    assert(original >= 0);
    int32_t id = bb_fd_adopt(&table, original);
    assert(id > 0);
    unsigned char object[16] = {0};
    memcpy(object + 12, &id, sizeof id);
    int lease = bb_fd_pin(&table, id);
    assert(lease >= 0 && (fcntl(lease, F_GETFD) & FD_CLOEXEC));
    assert(write(lease, "A", 1) == 1);
    assert(bb_fios_forward_sync_v638(object, sync_cb) && result == 0);

    pthread_t thread;
    assert(!pthread_create(&thread, NULL, close_worker, &id));
    assert(!pthread_join(thread, NULL));
    assert(bb_fd_pin(&table, id) == -EBADF && bb_fd_close(&table, id) == -EBADF);
    assert(dup2(fileno(b), original) == original);
    int32_t next = bb_fd_adopt(&table, original);
    assert(next > id);
    assert(bb_fios_forward_sync_v638(object, sync_cb) && result == -EBADF);
    assert(write(lease, "B", 1) == 1 && !fsync(lease) && !close(lease));
    char buf[2];
    assert(pread(fileno(a), buf, 2, 0) == 2 && !memcmp(buf, "AB", 2));
    assert(pread(fileno(b), buf, 2, 0) == 0);
    assert(!bb_fd_close(&table, next) && !fclose(a) && !fclose(b));

    assert(bb_fd_adopt(&table, -1) == -EBADF);
    assert(bb_fd_pin(&table, 0) == -EBADF && bb_fd_close(&table, 0) == -EBADF);
    int fd = open("/dev/null", O_RDONLY);
    assert(fd >= 0);
    int32_t ids[64];
    for (unsigned i = 0; i < 64; ++i) {
        int copy = dup(fd);
        assert(copy >= 0 && (ids[i] = bb_fd_adopt(&table, copy)) > 0);
    }
    assert(bb_fd_adopt(&table, fd) == -EMFILE && fcntl(fd, F_GETFD) >= 0);
    for (unsigned i = 0; i < 64; ++i) assert(!bb_fd_close(&table, ids[i]));
    table.last = INT32_MAX;
    assert(bb_fd_adopt(&table, fd) == -EOVERFLOW && !close(fd));
    assert(!pthread_mutex_destroy(&table.lock));
    puts("Fios2: sync, concurrent close with live pin, forced fd reuse, capacity, wrap OK");
}
