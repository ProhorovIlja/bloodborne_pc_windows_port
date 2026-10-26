// SPDX-License-Identifier: GPL-2.0-or-later
// Compile against the ACTUAL pinned + V97 patched Yharnam Together table.
// Test-only common/types.h supplies fixed integral aliases, no forked rules.
#include <cassert>
#include <iostream>
#include "bloodborne_flags.h"

using namespace Core::Bloodborne;
static_assert(RuleFor(6700).owner == FlagOwner::PerPlayer);
static_assert(RuleFor(6700).behaviour == 0u);
static_assert(RowFor(6700)!=nullptr);
static_assert(RowFor(6700)->first==6700 && RowFor(6700)->last==6700);
static_assert(RuleFor(6680).owner==FlagOwner::PerPlayer);
static_assert(RuleFor(9180).owner==FlagOwner::Session);
static_assert(RuleFor(6700).owner!=RuleFor(6701).owner);
static_assert(!RuleFor(6700).Has(FlagCarriesHome));
static_assert(!RuleFor(6700).Has(FlagGuestSetsInWorld));
static_assert(!RuleFor(6700).Has(FlagSharesClears));
int main(){
    assert(RuleFor(6700).owner==FlagOwner::PerPlayer);
    std::cout<<"SHYT_V97_REAL_PINNED_DOLL_LOCAL_FLAG_TEST_PASS\n";
}
