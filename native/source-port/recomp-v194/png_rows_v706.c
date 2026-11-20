/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <png.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct bb_png_input706 {
    const unsigned char *p;
    size_t left;
    unsigned char *stage;
};

static void bb_png_error706(png_structp p, png_const_charp message) {
    (void)message;
    png_longjmp(p,1);
}

static void bb_png_warn706(png_structp p, png_const_charp message) {
    (void)p;
    (void)message;
}

static void bb_png_read706(png_structp p, png_bytep out, png_size_t n) {
    struct bb_png_input706 *in=png_get_io_ptr(p);
    if (n>in->left) png_error(p,"truncated PNG input");
    memcpy(out,in->p,n);
    in->p+=n;
    in->left-=n;
}

/* Noninterlaced 8-bit RGB/RGBA only. No gamma conversion or channel
 * expansion. dst, width and height are disjoint; padding stays unchanged.
 * On failure none of the caller outputs are written. */
int bb_png_rows706(const void *data, size_t length, unsigned char *dst,
                   size_t capacity, size_t stride, unsigned channels,
                   uint32_t limit, uint32_t *width, uint32_t *height) {
    if (!data || !length || !dst || !width || !height || !limit || limit>8192 ||
        (channels!=3 && channels!=4)) return 0;
    struct bb_png_input706 *in=calloc(1,sizeof *in);
    if (!in) return 0;
    in->p=data;
    in->left=length;
    png_structp p=png_create_read_struct(PNG_LIBPNG_VER_STRING,NULL,bb_png_error706,bb_png_warn706);
    png_infop info=p ? png_create_info_struct(p) : NULL;
    volatile int ok=0;
    if (!info || setjmp(png_jmpbuf(p))) goto done;
    png_set_user_limits(p,limit,limit);
    png_set_read_fn(p,in,bb_png_read706);
    png_set_crc_action(p,PNG_CRC_ERROR_QUIT,PNG_CRC_ERROR_QUIT);
    png_read_info(p,info);
    png_uint_32 w=png_get_image_width(p,info), h=png_get_image_height(p,info);
    if (!w || !h || w>limit || h>limit || png_get_bit_depth(p,info)!=8 ||
        png_get_color_type(p,info)!=(channels==3 ? PNG_COLOR_TYPE_RGB : PNG_COLOR_TYPE_RGB_ALPHA) ||
        png_get_interlace_type(p,info)!=PNG_INTERLACE_NONE) goto done;
    size_t row=(size_t)w*channels;
    if (png_get_rowbytes(p,info)!=row || stride<row || capacity<row ||
        (h-1)>(capacity-row)/stride) goto done;
    in->stage=malloc(row*h);
    if (!in->stage) goto done;
    for (size_t y=0;y<h;++y) png_read_row(p,in->stage+y*row,NULL);
    png_read_end(p,info);
    for (size_t y=0;y<h;++y) memcpy(dst+y*stride,in->stage+y*row,row);
    *width=w;
    *height=h;
    ok=1;
done:
    if (p) png_destroy_read_struct(&p,&info,NULL);
    free(in->stage);
    free(in);
    return ok;
}
