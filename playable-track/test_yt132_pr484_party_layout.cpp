// SPDX-License-Identifier: GPL-2.0-or-later
// Builds the ACTUAL public upstream PR #484 header implementations.
// This tests no proprietary game bytes, no synthetic imitation of HUD layout.
#include <cassert>
#include <cmath>
#include "bbport_party_layout.h"
#include "bbport_portraits.h"

static_assert(BbPortraits::SlotCount == 4);
static_assert(BbPortraits::Magic(0)[1] == 0xc0);
static_assert(BbPortraits::Magic(3)[1] == 0xc3);
static_assert(BbPartyLayout::TeamCardsWidth ==
              5 * BbPartyLayout::TeamCardWidth + 4 * BbPartyLayout::TeamGap);
static_assert(BbPartyLayout::TeamButtonsWidth ==
              5 * BbPartyLayout::TeamButtonWidth + 4 * BbPartyLayout::TeamGap);
static_assert(BbPartyLayout::TeamCardsWidth < BbPartyLayout::TeamWindowWidth);
int main() {
    assert(std::abs(BbPartyLayout::TeamScreenScale(1.0f, 1920.0f)
                    - 1.0f) < 0.01f);
    assert(BbPartyLayout::TeamScreenScale(1.0f, 960.0f)
           < BbPartyLayout::TeamScreenScale(1.0f, 1920.0f));
    // A fifth hunter has four REMOTE portrait slots in the team's HUD.
    // This does not prove the fifth in-game character entity is instantiated.
    return 0;
}
