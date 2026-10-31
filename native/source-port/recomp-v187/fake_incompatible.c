/* Deliberately incompatible synthetic fixture, must be rejected by the host. */
#include "recomp_abi.h"
#include <stddef.h>
RC_EXPORT const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {
    (void)api;
    if (count) *count = 0;
    return NULL;
}
