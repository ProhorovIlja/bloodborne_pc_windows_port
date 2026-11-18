/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <png.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Native PNG boundary: no guest libpng structs or callbacks cross it.
 * Input, output and dimension pointers must be disjoint. A failure leaves
 * all caller outputs unchanged. The limits cap decoded size, not CPU time. */
int bb_png_rgba705(const void *data, size_t length, unsigned char *out,
                  size_t capacity, uint32_t limit, uint32_t *w, uint32_t *h) {
    if (!data || !length || !out || !w || !h || !limit || limit > 8192) return 0;
    png_image img = {0};
    unsigned char *stage = NULL;
    int ok = 0;
    img.version = PNG_IMAGE_VERSION;
    if (!png_image_begin_read_from_memory(&img,data,length)) goto done;
    if (!img.width || !img.height || img.width > limit || img.height > limit) goto done;
    img.format = PNG_FORMAT_RGBA;
    size_t size = (size_t)img.width * img.height * 4;
    if (size > capacity) goto done;
    stage = malloc(size);
    if (!stage || !png_image_finish_read(&img,NULL,stage,0,NULL)) goto done;
    memcpy(out,stage,size);
    *w = img.width;
    *h = img.height;
    ok = 1;
done:
    free(stage);
    png_image_free(&img);
    return ok;
}
