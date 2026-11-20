#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Usage: sh test_heap_donor_v545.sh /path/to/Paleblood
# An opt-in offline test. No download, game image, or donor runtime.
set -eu
[ "$#" = 1 ] || { echo "usage: $0 PALEBLOOD_CHECKOUT" >&2; exit 2; }
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) ;;
    *) echo "V545 fixture is validated only on Linux x86-64" >&2; exit 2 ;;
esac
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
pin=a8730c4956c1bfdc1b71de467c2841f5fe1cba0e
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
mkdir "$tmp/runtime"
for f in regular_heap.h regular_heap_allocate.cpp regular_heap_allocate_aligned.cpp regular_heap_free.cpp; do
    git -C "$1" show "$pin:game/engine/$f" > "$tmp/$f"
done
cat > "$tmp/runtime/original.h" <<'END'
#include "regular_heap.h"
extern "C" void *bb_engine_regular_heap_allocate_02485730(engine::regular_heap::Heap *,uint64_t);
#define RT_ORIGINAL(rva, name, signature) constexpr auto name = &bb_engine_regular_heap_allocate_02485730
END
cat > "$tmp/engine.h" <<'END'
#include <cstdlib>
#define RT_GLOBAL(rva, name, type) constexpr struct { const char *address() const { return ""; } } name{}
namespace engine { template<class... T> [[noreturn]] void fatal_error(T...) { std::abort(); } }
END
"${CC:-cc}" -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -pthread -c "$src/test_heap_donor_v545.c" -o "$tmp/test.o"
"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -O2 -I"$tmp" -pthread ${V545_LDFLAGS:-} "$tmp/test.o" "$tmp"/regular_heap*.cpp -o "$tmp/test"
"$tmp/test"
echo V545_HEAP_DONOR_PASS
"${CC:-cc}" -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -pthread -c "$src/test_heap_aperture_v549.c" -o "$tmp/test.o"
"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -O2 -I"$tmp" -pthread ${V545_LDFLAGS:-} "$tmp/test.o" "$tmp"/regular_heap*.cpp -o "$tmp/test"
"$tmp/test"
echo V549_HEAP_APERTURE_PASS
