/* SPDX-License-Identifier: GPL-2.0-or-later
 * Narrow, portable BND4 metadata index for a future Windows-native
 * Bloodborne game asset engine. Inspired by public SoulsFormats rules,
 * independently implemented in C with explicit overflow checks.
 * No dynamic allocation and no proprietary game data in source/CI.
 */
#include "native_bnd4_index_v361.h"
#include <stdint.h>
#include <string.h>

#define SHYT_BND4_HEADER_V361 0x40u
#define SHYT_BND4_RECORD_V361 0x24u
#define SHYT_BND4_MAX_FILES_V361 65536u
#define SHYT_BND4_MAX_ARCHIVE_V361 (512ull*1024ull*1024ull)

static uint32_t le32_v361(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static uint64_t le64_v361(const unsigned char *p) {
    return (uint64_t)le32_v361(p) | ((uint64_t)le32_v361(p+4)<<32);
}
static int bounded_v361(uint64_t start, uint64_t count, uint64_t limit) {
    return start<=limit && count<=limit-start;
}
static int safe_file_v361(
    const unsigned char *p, uint64_t bytes, uint64_t headers_end,
    uint64_t records_end, uint64_t names_end, uint32_t number,
    ShytNativeBnd4FileV361 *out) {
    const uint64_t record=(uint64_t)SHYT_BND4_HEADER_V361+
                          (uint64_t)number*SHYT_BND4_RECORD_V361;
    if (!bounded_v361(record,SHYT_BND4_RECORD_V361,bytes) ||
        record+SHYT_BND4_RECORD_V361>records_end)
        return 0;
    const unsigned char *f=p+(size_t)record;
    /* Raw 0x40=stored, 0xC0=per-file compressed. All other
     * combinations are unverified and fail closed. */
    if ((f[0]!=0x40u && f[0]!=0xC0u) ||
        f[1] || f[2] || f[3] ||
        le32_v361(f+4)!=0xFFFFFFFFu)
        return 0;
    const uint64_t stored=le64_v361(f+8);
    const uint64_t original=le64_v361(f+16);
    const uint64_t data_offset=(uint64_t)le32_v361(f+24);
    const uint32_t name_offset=le32_v361(f+32);
    const int compressed=f[0]==0xC0u;
    if ((!compressed && stored!=original) ||
        stored>SHYT_BND4_MAX_ARCHIVE_V361 ||
        original>SHYT_BND4_MAX_ARCHIVE_V361 ||
        (stored!=0 && (data_offset<headers_end ||
          !bounded_v361(data_offset,stored,bytes))) ||
        (stored==0 && data_offset!=0 && data_offset<headers_end) ||
        (stored==0 && !bounded_v361(data_offset,0,bytes)) ||
        name_offset<records_end || name_offset>=names_end ||
        (name_offset&1u))
        return 0;
    /* Names are UTF16LE, NUL-terminated inside the INDEX area. Do not
     * interpret as filesystem paths or allow a late read into payload.
     * Scan bounded by the verified header region only. */
    uint64_t pos=name_offset;
    uint32_t code_units=0;
    int terminated=0;
    while(bounded_v361(pos,2,names_end)) {
        if (p[(size_t)pos]==0 && p[(size_t)pos+1]==0) {
            terminated=1;
            break;
        }
        ++code_units;
        pos+=2;
    }
    if (!terminated || !code_units) return 0;
    if (out) {
        memset(out,0,sizeof(*out));
        out->data_offset=data_offset;
        out->stored_bytes=stored;
        out->original_bytes=original;
        out->file_id=le32_v361(f+28);
        out->name_utf16_offset=name_offset;
        out->name_utf16_code_units=code_units;
        out->compressed=(uint8_t)compressed;
    }
    return 1;
}

int shyt_native_bnd4_index_probe_v361(
    const void *data,size_t bytes,ShytNativeBnd4IndexV361 *out) {
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!data || bytes<SHYT_BND4_HEADER_V361 ||
        (uint64_t)bytes>SHYT_BND4_MAX_ARCHIVE_V361)
        return 0;
    const unsigned char *p=(const unsigned char *)data;
    /* Real 1.09 BB and DS3 samples: LE, UTF16, raw format 0x74,
     * record size 0x24; explicit refusal of ambiguous variants. */
    if (memcmp(p,"BND4",4)!=0 || p[4] || p[5] || p[6] || p[7] ||
        p[8] || p[9] || p[10]!=1u || p[11] ||
        le64_v361(p+16)!=SHYT_BND4_HEADER_V361 ||
        le64_v361(p+32)!=SHYT_BND4_RECORD_V361 ||
        p[48]!=1u || p[49]!=0x74u ||
        (p[50]!=0u && p[50]!=4u) || p[51] ||
        le32_v361(p+52)!=0u)
        return 0;
    const uint32_t count=le32_v361(p+12);
    const uint64_t headers_end=le64_v361(p+40);
    const uint64_t records_end=(uint64_t)SHYT_BND4_HEADER_V361+
                      (uint64_t)count*SHYT_BND4_RECORD_V361;
    if (!count || count>SHYT_BND4_MAX_FILES_V361 ||
        !bounded_v361(0,records_end,headers_end) ||
        headers_end>bytes)
        return 0;
    const uint64_t hash_offset=le64_v361(p+56);
    if (p[50]==0u) {
        if (hash_offset!=0u) return 0;
    } else {
        /* SoulsFormats BND4 extended=4: [hash-offset:8][buckets:4]
         * [0x10,8,8,0][groups:8*buckets][hash,index:8*files].
         */
        if (hash_offset<records_end ||
            !bounded_v361(hash_offset,16,headers_end))
            return 0;
        const unsigned char *ht=p+(size_t)hash_offset;
        const uint64_t hashes_offset=le64_v361(ht);
        const uint32_t buckets=le32_v361(ht+8);
        const uint64_t groups=hash_offset+16u;
        if (ht[12]!=0x10u || ht[13]!=8u || ht[14]!=8u ||
            ht[15]!=0 || !buckets ||
            buckets>SHYT_BND4_MAX_FILES_V361 ||
            !bounded_v361(groups,(uint64_t)buckets*8u,headers_end) ||
            hashes_offset<groups+(uint64_t)buckets*8u ||
            !bounded_v361(hashes_offset,(uint64_t)count*8u,headers_end))
            return 0;
        uint64_t total_entries=0;
        for (uint32_t i=0;i<buckets;++i) {
            const unsigned char *g=p+(size_t)groups+(size_t)i*8u;
            const uint32_t group_count=le32_v361(g);
            const uint32_t group_start=le32_v361(g+4);
            if (group_start>count || group_count>count-group_start)
                return 0;
            total_entries+=group_count;
        }
        if (total_entries!=count) return 0;
        for (uint32_t i=0;i<count;++i) {
            /* No trust in hash-to-file index before matching path. */
            const uint32_t number=le32_v361(
                p+(size_t)hashes_offset+(size_t)i*8u+4u);
            if (number>=count) return 0;
        }
    }
    for (uint32_t i=0;i<count;++i) {
        if (!safe_file_v361(p,(uint64_t)bytes,headers_end,
                            records_end,p[50]==4u?hash_offset:headers_end,i,0))
            return 0;
    }
    out->file_count=count;
    out->header_end=headers_end;
    out->hash_table_offset=hash_offset;
    out->extended=p[50];
    return 1;
}

int shyt_native_bnd4_file_at_v361(
    const void *data,size_t bytes,
    const ShytNativeBnd4IndexV361 *index,uint32_t file_number,
    ShytNativeBnd4FileV361 *out) {
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!data || !index || file_number>=index->file_count ||
        index->file_count>SHYT_BND4_MAX_FILES_V361 ||
        (uint64_t)bytes>SHYT_BND4_MAX_ARCHIVE_V361 ||
        index->header_end>bytes)
        return 0;
    const uint64_t records_end=(uint64_t)SHYT_BND4_HEADER_V361+
                          (uint64_t)index->file_count*SHYT_BND4_RECORD_V361;
    if (records_end>index->header_end)
        return 0;
    return safe_file_v361((const unsigned char *)data,
        (uint64_t)bytes,index->header_end,records_end,
        index->extended==4u?index->hash_table_offset:index->header_end,
        file_number,out);
}
