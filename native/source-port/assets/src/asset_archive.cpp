// SPDX-License-Identifier: GPL-2.0-or-later
// V186: Native, read-only, bounded FromSoftware DCX-DFLT/BND4 asset access.
// No PS4 ABI, guest executable, command processor, or emulator dependency.
#include "asset_archive.hpp"
#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <zlib.h>

namespace bb::native {
namespace {
using Bytes=std::span<const std::uint8_t>;
void require(bool ok, const char* why){if(!ok)throw std::runtime_error(why);}
void region(Bytes d, std::uint64_t at, std::uint64_t count){
    require(at<=d.size() && count<=d.size()-static_cast<std::size_t>(at),"archive offsets outside file");
}
std::uint32_t le32(Bytes d,std::size_t p){region(d,p,4);return std::uint32_t(d[p])|(std::uint32_t(d[p+1])<<8)|(std::uint32_t(d[p+2])<<16)|(std::uint32_t(d[p+3])<<24);}
std::uint64_t le64(Bytes d,std::size_t p){return std::uint64_t(le32(d,p))|(std::uint64_t(le32(d,p+4))<<32);}
std::uint32_t be32(Bytes d,std::size_t p){region(d,p,4);return (std::uint32_t(d[p])<<24)|(std::uint32_t(d[p+1])<<16)|(std::uint32_t(d[p+2])<<8)|std::uint32_t(d[p+3]);}
bool literal(Bytes d,std::size_t p, const char* s,std::size_t n){return p<=d.size() && n<=d.size()-p && std::memcmp(d.data()+p,s,n)==0;}
std::vector<std::uint8_t> inflate_exact(Bytes compressed,std::size_t expected){
    require(expected>0 && expected<=AssetArchive::max_decoded_bytes,"decompression output over budget");
    require(compressed.size()<=AssetArchive::max_file_bytes,"compressed payload over budget");
    require(compressed.size()<=std::numeric_limits<uInt>::max() && expected<=std::numeric_limits<uInt>::max(),"zlib size overflow");
    std::vector<std::uint8_t> out(expected);
    z_stream z{};
    z.next_in=const_cast<Bytef*>(compressed.data());
    z.avail_in=static_cast<uInt>(compressed.size());
    z.next_out=out.data();
    z.avail_out=static_cast<uInt>(out.size());
    require(inflateInit(&z)==Z_OK,"zlib failed to initialize");
    int status=inflate(&z,Z_FINISH);
    const bool valid=status==Z_STREAM_END && z.total_in==compressed.size() && z.total_out==expected;
    inflateEnd(&z);
    require(valid,"zlib stream incomplete, oversized, trailing, or corrupt");
    return out;
}
std::u16string read_name(Bytes d,std::size_t at){
    require(at>=0x40 && at<d.size(),"BND4 virtual-name offset invalid");
    std::u16string name;
    for(std::size_t n=0;n<1024;n++){
        region(d,at+2*n,2);
        std::uint16_t u=std::uint16_t(d[at+2*n])|(std::uint16_t(d[at+2*n+1])<<8);
        if(u==0){require(!name.empty(),"empty virtual asset name");return name;}
        require(u>=0x20 || u==0x09,"invalid virtual asset name character");
        name.push_back(static_cast<char16_t>(u));
    }
    throw std::runtime_error("unterminated BND4 virtual name");
}
} // namespace

AssetArchive AssetArchive::from_bytes(Bytes file){
    require(file.size()>=0x4c,"DCX file too short");
    require(file.size()<=max_file_bytes,"DCX file over budget");
    require(literal(file,0,"DCX\0",4) && literal(file,0x18,"DCS\0",4) &&
            literal(file,0x24,"DCP\0",4) && literal(file,0x28,"DFLT",4) &&
            literal(file,0x44,"DCA\0",4) && be32(file,0x48)==8,
            "only DCX DFLT with expected checked header is supported");
    auto unpacked=be32(file,0x1c),packed=be32(file,0x20);
    // Dark Souls III aligns the compressed DCX container to 16 bytes, while
    // Bloodborne often omits that padding. Both share the same DFLT payload.
    require(packed<=file.size()-0x4c && file.size()-0x4c-packed<=15,
            "DCX compressed length/padding mismatch");
    auto pad=file.subspan(0x4c+packed);
    require(std::all_of(pad.begin(),pad.end(),[](std::uint8_t v){return v==0;}),
            "nonzero trailing DCX bytes");
    require(unpacked>=0x40 && unpacked<=max_decoded_bytes,"DCX decoded length over budget");
    AssetArchive archive;
    archive.data_=inflate_exact(file.subspan(0x4c,packed),unpacked);
    Bytes bytes=archive.data_;
    require(literal(bytes,0,"BND4",4),"expected BND4, not unrelated asset");
    // V186 initially supports only the endian/filename variant directly
    // verified on actual private Bloodborne 1.09 and Dark Souls III PC assets.
    require(bytes[8]==0 && bytes[9]==0 && bytes[10]==1 && bytes[11]==0,
            "unsupported BND4 endian variant");
    const auto count=le32(bytes,0x0c);
    const auto hsize=le64(bytes,0x10);
    const auto esize=le64(bytes,0x20);
    require(hsize==0x40 && esize==0x24,"unsupported BND4 record size");
    require(bytes[0x30]==1 && (bytes[0x31]==0x54 || bytes[0x31]==0x74),
            "unsupported BND4 name encoding/record flags");
    require(count<=100000 && std::uint64_t(count)*esize<=bytes.size()-hsize,
            "BND4 file table over budget");
    archive.entries_.reserve(count);
    const auto table_end=hsize+std::uint64_t(count)*esize;
    for(std::size_t i=0;i<count;i++){
        const auto pos=static_cast<std::size_t>(hsize+i*esize);
        BinderEntry e;
        e.flags=bytes[pos];
        require(e.flags==0x40 || e.flags==0x00 || e.flags==0x02 ||
                e.flags==0x03 || e.flags==0x0a || e.flags==0xc0,
                "unsupported BND4 file compression flags");
        require(bytes[pos+1]==0 && bytes[pos+2]==0 && bytes[pos+3]==0 &&
                le32(bytes,pos+4)==0xffffffffu,"BND4 record header invalid");
        e.stored_size=le64(bytes,pos+8);
        e.decoded_size=le64(bytes,pos+16);
        e.data_offset=le32(bytes,pos+24);
        e.id=static_cast<std::int32_t>(le32(bytes,pos+28));
        const auto name_offset=le32(bytes,pos+32);
        require(e.data_offset>=table_end && e.stored_size<=max_decoded_bytes,
                "BND4 member outside data section or over budget");
        region(bytes,e.data_offset,e.stored_size);
        require(e.decoded_size<=max_decoded_bytes,"BND4 decoded member over budget");
        e.name=read_name(bytes,name_offset);
        if(e.flags!=0x03 && e.flags!=0xc0)
            require(e.stored_size==e.decoded_size,"uncompressed BND4 member size mismatch");
        archive.entries_.push_back(std::move(e));
    }
    return archive;
}

AssetArchive AssetArchive::from_file(const std::filesystem::path& path){
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    require(bool(in),"cannot open read-only asset file");
    const auto sz=in.tellg();
    require(sz>=0 && static_cast<std::uint64_t>(sz)<=max_file_bytes,"file size over budget");
    in.seekg(0);
    std::vector<std::uint8_t> file(static_cast<std::size_t>(sz));
    if(!file.empty())in.read(reinterpret_cast<char*>(file.data()),static_cast<std::streamsize>(file.size()));
    require(bool(in),"failed to read full asset");
    return from_bytes(file);
}

std::vector<std::uint8_t> AssetArchive::payload(std::size_t idx) const{
    require(idx<entries_.size(),"BND4 member index out of range");
    const auto& e=entries_[idx];
    Bytes file=data_;
    auto raw=file.subspan(e.data_offset,static_cast<std::size_t>(e.stored_size));
    if(e.flags==0x03 || e.flags==0xc0)
        return inflate_exact(raw,static_cast<std::size_t>(e.decoded_size));
    return {raw.begin(),raw.end()};
}
} // namespace bb::native
