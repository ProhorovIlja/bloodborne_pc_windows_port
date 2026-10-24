// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// A network endpoint cannot silently acquire another account's identity while
// retaining the old virtual-address route, party state and reliable packets.
namespace SeamlessHunt::LinkRebind {
template<class Id>
constexpr bool MustRetire(bool endpoint_present,const Id& current,const Id& claimed) {
    return endpoint_present && current != claimed;
}
}
