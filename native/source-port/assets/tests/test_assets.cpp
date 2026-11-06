// SPDX-License-Identifier: GPL-2.0-or-later
#include "asset_archive.hpp"
#include <zlib.h>
#include <cassert>
#define CHECK(cond) do { if (!(cond)) throw std::runtime_error("native test failed: " #cond); } while (false)
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using V=std::vector<std::uint8_t>;
namespace {
void w32(V&v,std::size_t at,std::uint32_t x){
    CHECK(at+4<=v.size());
    for(std::size_t j=0;j<4;j++)v[at+j]=static_cast<std::uint8_t>(x>>(j*8));
}
void w64(V&v,std::size_t at,std::uint64_t x){
    w32(v,at,static_cast<std::uint32_t>(x));w32(v,at+4,static_cast<std::uint32_t>(x>>32));
}
void be32(V&v,std::size_t at,std::uint32_t x){for(std::size_t j=0;j<4;j++)v[at+j]=static_cast<std::uint8_t>(x>>(24-j*8));}
void text(V&v,std::size_t at,const char*p){std::memcpy(v.data()+at,p,std::strlen(p));}
V pack(const V&v){
    uLongf n=compressBound(static_cast<uLong>(v.size()));
    V out(n);const auto r=compress2(out.data(),&n,v.data(),static_cast<uLong>(v.size()),Z_BEST_COMPRESSION);
    CHECK(r==Z_OK);out.resize(static_cast<std::size_t>(n));return out;
}
V make_bnd(bool compress_member=false){
    const V payload={'n','a','t','i','v','e',' ','a','s','s','e','t'};
    const auto stored=compress_member?pack(payload):payload;
    V b(0xa0+stored.size());text(b,0,"BND4");b[10]=1;
    w32(b,12,1);w64(b,16,0x40);text(b,24,"10G29R1");w64(b,32,0x24);
    w64(b,40,0xa0);b[48]=1;b[49]=0x54;
    b[64]=compress_member?0x03:0x40;w32(b,68,0xffffffffu);
    w64(b,72,stored.size());w64(b,80,payload.size());w32(b,88,0xa0);
    w32(b,92,15);w32(b,96,0x70);
    const char*name="GX_Test";
    for(std::size_t i=0;i<std::strlen(name);i++)b[0x70+i*2]=static_cast<std::uint8_t>(name[i]);
    std::memcpy(b.data()+0xa0,stored.data(),stored.size());return b;
}
V make_dcx(const V& payload){
    const auto packed=pack(payload);V d(76+packed.size());
    text(d,0,"DCX");be32(d,4,0x10000);be32(d,8,0x18);be32(d,12,0x24);
    be32(d,16,0x44);be32(d,20,0x4c);text(d,24,"DCS");
    be32(d,28,static_cast<std::uint32_t>(payload.size()));
    be32(d,32,static_cast<std::uint32_t>(packed.size()));
    text(d,36,"DCP");text(d,40,"DFLT");be32(d,44,0x20);
    d[48]=9;d[66]=1;d[67]=1;
    text(d,68,"DCA");be32(d,72,8);
    std::memcpy(d.data()+76,packed.data(),packed.size());return d;
}
template<class F>void rejects(F f){bool thrown=false;try{f();}catch(const std::exception&){thrown=true;}CHECK(thrown);}
void exercise(){
    using bb::native::AssetArchive;
    auto raw=make_bnd();auto dcx=make_dcx(raw);
    const auto a=AssetArchive::from_bytes(dcx);
    CHECK(a.entries().size()==1);
    CHECK(a.entries()[0].name==u"GX_Test");
    CHECK(a.entries()[0].id==15);
    CHECK(a.payload(0)==V({'n','a','t','i','v','e',' ','a','s','s','e','t'}));
    rejects([&]{(void)a.payload(1);});
    // Two real variants: Bloodborne unpadded DCX; DS3 aligned-to-16 DCX.
    auto aligned=dcx;
    while(aligned.size()%16)aligned.push_back(0);
    CHECK(AssetArchive::from_bytes(aligned).entries().size()==1);
    auto nonzero=aligned;
    if(nonzero.size()>dcx.size()){
        nonzero.back()=1;
        rejects([&]{(void)AssetArchive::from_bytes(nonzero);});
    }
    auto too_much_padding=dcx;
    too_much_padding.insert(too_much_padding.end(),16,0);
    rejects([&]{(void)AssetArchive::from_bytes(too_much_padding);});
    auto compressed=AssetArchive::from_bytes(make_dcx(make_bnd(true)));
    CHECK(compressed.payload(0)==a.payload(0));
    auto bad=dcx;bad[0]='X';rejects([&]{(void)AssetArchive::from_bytes(bad);});
    bad=dcx;bad[32]^=1;rejects([&]{(void)AssetArchive::from_bytes(bad);});
    bad=dcx;bad.back()^=1;rejects([&]{(void)AssetArchive::from_bytes(bad);});
    bad=dcx;bad.resize(75);rejects([&]{(void)AssetArchive::from_bytes(bad);});
    raw=make_bnd();raw[10]=0;rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    raw=make_bnd();w32(raw,12,1000000);rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    raw=make_bnd();w32(raw,96,0xfffffffeu);rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    raw=make_bnd();w32(raw,88,0xffffffffu);rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    raw=make_bnd();w64(raw,72,static_cast<std::uint64_t>(AssetArchive::max_decoded_bytes)+1);rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    raw=make_bnd();w32(raw,96,raw.size()-2);raw[raw.size()-2]='A';raw.back()='A';rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    raw=make_bnd();raw[64]=0x9f;rejects([&]{(void)AssetArchive::from_bytes(make_dcx(raw));});
    std::cout<<"native_source_port_asset_parser_synthetic=PASS\n";
}
}
int main(){exercise();}
