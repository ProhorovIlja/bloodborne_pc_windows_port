/* SPDX-License-Identifier: GPL-2.0-or-later
 * V354: FromSoftware DCX_DFLT_10000_44_9 envelope reader.
 * Derived from public SoulsFormats DCX.cs and Souls Modding Wiki.
 * No proprietary input embedded, no decompressor or emulator.
 */
#include "native_dcx_dflt_header_v354.h"
#include <string.h>

static uint32_t be32_v354(const unsigned char *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|
           ((uint32_t)p[2]<<8)|(uint32_t)p[3];
}
int shyt_native_dcx_dflt_probe_v354(
    const void *header,size_t header_bytes,uint64_t file_size,
    ShytNativeDcxDfltHeaderV354 *out) {
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!header || header_bytes<SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354)
        return 0;
    const unsigned char *p=(const unsigned char *)header;
    if (memcmp(p,"DCX\0",4)!=0 ||
        (be32_v354(p+4)!=0x10000u && be32_v354(p+4)!=0x11000u) ||
        be32_v354(p+8)!=0x18u || be32_v354(p+12)!=0x24u ||
        /* BB 1.09 DFLT_10000_24_9 uses 0x24/0x2C, while
         * DS3 DFLT_10000_44_9 uses 0x44/0x4C. Pair values: do
         * not let a malformed hybrid bypass the header gate. */
        !((be32_v354(p+16)==0x24u && be32_v354(p+20)==0x2Cu &&
           be32_v354(p+4)==0x10000u && p[48]==9u && p[56]==0u) ||
          (be32_v354(p+16)==0x44u && be32_v354(p+20)==0x4Cu)) ||
        memcmp(p+24,"DCS\0",4)!=0 ||
        memcmp(p+36,"DCP\0",4)!=0 || memcmp(p+40,"DFLT",4)!=0 ||
        be32_v354(p+44)!=0x20u ||
        (p[48]!=8u && p[48]!=9u) ||
        p[49] || p[50] || p[51] ||
        be32_v354(p+52)!=0 ||
        p[57] || p[58] || p[59] ||
        be32_v354(p+60)!=0 || be32_v354(p+64)!=0x00010100u ||
        memcmp(p+68,"DCA\0",4)!=0 || be32_v354(p+72)!=8u)
        return 0;
    const uint32_t plain=be32_v354(p+28);
    const uint32_t packed=be32_v354(p+32);
    const uint64_t offset=SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354;
    if (!plain || packed<2 || plain>SHYT_NATIVE_DCX_MAX_OUTPUT_V354 ||
        packed>SHYT_NATIVE_DCX_MAX_INPUT_V354 ||
        (uint64_t)packed>file_size ||
        file_size<offset || (uint64_t)packed>file_size-offset ||
        (uint64_t)plain>256ull*(uint64_t)packed)
        return 0;
    out->uncompressed_bytes=plain;
    out->compressed_bytes=packed;
    out->payload_offset=offset;
    out->compression_level=p[48];
    return 1;
}
