// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Regression based on upstream Yharnam Together PR #365, tested against
// the original pinned parser AFTER V94's exact-source backport.
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <QByteArray>
#include "stream_extractor.h"

static QByteArray Packet(std::uint32_t count,const QByteArray& bytes) {
    QByteArray out(4,'\0');
    std::memcpy(out.data(),&count,4);
    return out+bytes;
}
#define MUST(test) do { \
    if(!(test)){std::cerr<<"V94 failed at line "<<__LINE__<<": "<<#test<<"\n";return 1;} \
} while(false)

int main() {
    {
        StreamExtractor in(Packet(3,"abc"));
        MUST(in.getRawData()=="abc");
        MUST(!in.error());
    }
    {
        StreamExtractor in(Packet(4,"abc"));
        MUST(in.getRawData().isEmpty());
        MUST(in.error());
    }
    for(std::uint32_t count:{
       0x7fffffffu,0x80000000u,0xfffffff0u,0xffffffffu}) {
        StreamExtractor in(Packet(count,"abc"));
        MUST(in.getRawData().isEmpty());
        MUST(in.error());
    }
    {
        StreamExtractor in(QByteArray("abc"));
        MUST(in.getBytes(-1).isEmpty());
        MUST(in.error());
    }
    {
        StreamExtractor in(QByteArray("abc"));
        MUST(in.peekBytes(-1).isEmpty());
        MUST(!in.error());
        MUST(in.peekBytes(4).isEmpty());
        MUST(in.getBytes(3)=="abc");
        MUST(in.peekBytes(1).isEmpty());
        MUST(!in.error());
    }
    std::cout<<"SHYT_V94_UPSTREAM_PREAUTH_STREAM_BOUNDARIES_PASS\n";
}
