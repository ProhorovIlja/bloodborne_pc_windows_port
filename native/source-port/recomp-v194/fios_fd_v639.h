/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_FIOS_FD_V639_H
#define BB_FIOS_FD_V639_H
/* Linux proof: positive logical handles, not PS4 errors or path semantics.
 * Table starts empty; fd ownership transfers only on successful adoption.
 * A duplicate pins the open file description through a concurrent close. */
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <unistd.h>

struct bb_fd_row { int32_t id; int fd; };
struct bb_fd_table {
    pthread_mutex_t lock;
    uint32_t last;
    struct bb_fd_row row[64];
};
#define BB_FD_INIT { .lock = PTHREAD_MUTEX_INITIALIZER }

static inline int32_t bb_fd_adopt(struct bb_fd_table *t, int fd) {
    if (fd < 0) return -EBADF;
    int32_t id = -EMFILE;
    pthread_mutex_lock(&t->lock);
    if (t->last < INT32_MAX) {
        for (unsigned i = 0; i < 64; ++i) if (!t->row[i].id) {
            id = (int32_t)++t->last;
            t->row[i] = (struct bb_fd_row){id, fd};
            break;
        }
    } else id = -EOVERFLOW;
    pthread_mutex_unlock(&t->lock);
    return id;
}

static inline int bb_fd_pin(struct bb_fd_table *t, int32_t id) {
    if (id <= 0) return -EBADF;
    int result = -EBADF;
    pthread_mutex_lock(&t->lock);
    for (unsigned i = 0; i < 64; ++i) if (t->row[i].id == id) {
        result = fcntl(t->row[i].fd, F_DUPFD_CLOEXEC, 0);
        if (result < 0) result = -errno;
        break;
    }
    pthread_mutex_unlock(&t->lock);
    return result;
}

static inline int bb_fd_close(struct bb_fd_table *t, int32_t id) {
    if (id <= 0) return -EBADF;
    int fd = -1;
    pthread_mutex_lock(&t->lock);
    for (unsigned i = 0; i < 64; ++i) if (t->row[i].id == id) {
        fd = t->row[i].fd;
        t->row[i].id = 0;
        break;
    }
    pthread_mutex_unlock(&t->lock);
    if (fd < 0) return -EBADF;
    return close(fd) < 0 ? -errno : 0;
}

static inline int bb_fd_sync(struct bb_fd_table *t, int32_t id) {
    int fd = bb_fd_pin(t, id);
    if (fd < 0) return fd;
    int rc;
    do { rc = fsync(fd); } while (rc < 0 && errno == EINTR);
    int result = rc < 0 ? -errno : 0;
    if (close(fd) < 0 && !result) result = -errno;
    return result;
}
#endif
