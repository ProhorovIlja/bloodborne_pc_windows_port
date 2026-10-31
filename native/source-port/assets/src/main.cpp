// SPDX-License-Identifier: GPL-2.0-or-later
#include "asset_archive.hpp"
#include <cstdint>
#include <exception>
#include <iostream>
#include <map>
#include <string>
int main(int argc,char**argv){
    if(argc!=2 && argc!=3){std::cerr<<"usage: bb-native-assets FILE.dcx [SECOND_FILE.dcx]\n";return 2;}
    try {
        auto a=bb::native::AssetArchive::from_file(argv[1]);
        std::uint64_t bytes=0;
        for(const auto& e:a.entries())bytes+=e.decoded_size;
        // No private game path, names or proprietary binary bytes in stdout.
        std::cout<<"native_dcx_bnd4=PASS files="<<a.entries().size()<<" member_bytes="<<bytes<<"\n";
        if(argc==3){
            auto b=bb::native::AssetArchive::from_file(argv[2]);
            std::map<std::u16string,std::uint64_t> first;
            for(const auto& e:a.entries())first.emplace(e.name,e.decoded_size);
            std::size_t shared=0,different=0;
            for(const auto& e:b.entries()){
                auto f=first.find(e.name);
                if(f!=first.end()){shared++;if(f->second!=e.decoded_size)different++;}
            }
            std::cout<<"native_schema_compare=PASS other_files="<<b.entries().size()
                     <<" shared_virtual_names="<<shared<<" differing_member_sizes="<<different<<"\n";
        }
        return 0;
    }catch(const std::exception& e){
        // A fixed-category diagnostic. In the calling environment, private paths
        // must not be echoed by std::filesystem exceptions.
        std::cerr<<"native_dcx_bnd4=REJECT malformed_or_unsupported_asset\n";
        return 1;
    }
}
