/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host-owned startup lifecycle, derived from the observed retail call
 * order. No PS4 image, host exit(), global atexit(), or guest pointers.
 * Adapters are explicit; this is not an implementation of PS4 libc.
 */
#ifndef SHYT_NATIVE_CRT_V409_H
#define SHYT_NATIVE_CRT_V409_H
#include <stddef.h>
#include <stdint.h>

enum { SHYT_CRT_MAX_EXIT_V409 = 64 };
enum ShytCrtPhaseV409 {
    SHYT_CRT_NEW_V409, SHYT_CRT_ENV_V409, SHYT_CRT_INIT_V409,
    SHYT_CRT_MAIN_V409, SHYT_CRT_NOTIFY_V409, SHYT_CRT_EXIT_V409,
    SHYT_CRT_DONE_V409, SHYT_CRT_FAILED_V409
};
typedef struct ShytCrtV409 ShytCrtV409;
typedef void (*ShytExitFnV409)(void *);
typedef struct {
    ShytExitFnV409 fn;
    void *context;
} ShytExitEntryV409;
struct ShytCrtV409 {
    enum ShytCrtPhaseV409 phase;
    size_t count;
    ShytExitEntryV409 handlers[SHYT_CRT_MAX_EXIT_V409];
};

typedef struct {
    int (*setup_environment)(void *, int, char *const *, char *const *);
    ShytExitEntryV409 loader_shutdown;
    ShytExitEntryV409 image_shutdown;
    int (*run_initializers)(void *, ShytCrtV409 *);
    int (*main_entry)(void *, ShytCrtV409 *, int, char *const *, void *);
    void (*main_returned)(void *, int);
} ShytCrtHooksV409;

/* Single-controller, one-shot object initialized to zero. Adapters must
 * return normally and must not mutate the object's internals. */
static inline int shyt_crt_register_v409(
    ShytCrtV409 *crt, ShytExitEntryV409 entry) {
    if (!crt || !entry.fn || crt->count >= SHYT_CRT_MAX_EXIT_V409 ||
        (crt->phase != SHYT_CRT_INIT_V409 && crt->phase != SHYT_CRT_MAIN_V409))
        return 0;
    crt->handlers[crt->count++] = entry;
    return 1;
}
static inline void shyt_crt_drain_v409(ShytCrtV409 *crt) {
    crt->phase = SHYT_CRT_EXIT_V409;
    while (crt->count) {
        ShytExitEntryV409 entry = crt->handlers[--crt->count];
        crt->handlers[crt->count] = (ShytExitEntryV409){0};
        entry.fn(entry.context);
    }
}

/* Host argv/envp are trusted pointers, not a guest launch frame. On
 * pre-main failure no main/status notification occurs; after initializer
 * failure registered cleanup runs, and status_out stays untouched. A
 * failing environment adapter must clean up its own partial setup. */
static inline int shyt_crt_run_v409(ShytCrtV409 *crt,
    const ShytCrtHooksV409 *hooks, void *context, int argc,
    char *const *argv, char *const *envp, int *status_out) {
    int status;
    if (!crt || crt->phase != SHYT_CRT_NEW_V409 || crt->count ||
        !hooks || !hooks->setup_environment || !hooks->loader_shutdown.fn ||
        !hooks->image_shutdown.fn || !hooks->run_initializers ||
        !hooks->main_entry || !hooks->main_returned ||
        !status_out || argc < 0 || argc > 4096 || !argv || argv[argc])
        return 0;
    for (int i = 0; i < argc; ++i)
        if (!argv[i]) return 0;
    crt->phase = SHYT_CRT_ENV_V409;
    if (!hooks->setup_environment(context, argc, argv, envp)) {
        crt->phase = SHYT_CRT_FAILED_V409;
        return 0;
    }
    crt->phase = SHYT_CRT_INIT_V409;
    if (!shyt_crt_register_v409(crt, hooks->loader_shutdown) ||
        !shyt_crt_register_v409(crt, hooks->image_shutdown) ||
        !hooks->run_initializers(context, crt)) {
        shyt_crt_drain_v409(crt);
        crt->phase = SHYT_CRT_FAILED_V409;
        return 0;
    }
    crt->phase = SHYT_CRT_MAIN_V409;
    /* The audited retail wrapper supplies zero as main's third argument.
     * Environment setup is separate; do not pass host envp to main. */
    status = hooks->main_entry(context, crt, argc, argv, NULL);
    crt->phase = SHYT_CRT_NOTIFY_V409;
    hooks->main_returned(context, status);
    shyt_crt_drain_v409(crt);
    *status_out = status;
    crt->phase = SHYT_CRT_DONE_V409;
    return 1;
}
#endif
