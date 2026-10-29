// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "invader_dbno_policy.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::InGame;
int main() {
    // DBNO on: a downed hostile stays in the fight while an ally can revive.
    InvaderDbnoSide trio(true);
    assert(trio.Join("red") && trio.Join("blue") && trio.Join("violet"));
    assert(!trio.Join("fourth") && !trio.Join("red") && !trio.Join(""));
    assert(trio.Down("red",10)==InvaderEvent::Downed);
    assert(trio.DownCount()==1 && trio.ConnectedCount()==3);
    assert(trio.Down("red",10)==InvaderEvent::Ignored); // duplicate
    assert(trio.Revive("red","red",11)==InvaderEvent::Ignored); // cannot self-revive
    assert(trio.Revive("red","outsider",11)==InvaderEvent::Ignored);
    assert(trio.Revive("red","blue",11)==InvaderEvent::Revived);
    assert(trio.Down("red",10)==InvaderEvent::Ignored); // stale death after revive
    assert(trio.Down("red",12)==InvaderEvent::Downed);
    assert(trio.Down("blue",13)==InvaderEvent::Downed);
    assert(trio.AliveCount()==1 && !trio.Ended());
    assert(trio.Revive("blue","violet",14)==InvaderEvent::Revived);
    assert(trio.Down("violet",15)==InvaderEvent::Downed);
    assert(trio.AliveCount()==1 && trio.DownCount()==2);
    assert(trio.Down("blue",16)==InvaderEvent::SideDefeated);
    assert(trio.Ended() && trio.ConnectedCount()==0);
    assert(trio.Revive("red","blue",17)==InvaderEvent::Ignored);
    assert(!trio.Join("newcomer")); // already closed
    // DBNO off: every downed invader leaves immediately, without ejecting others.
    InvaderDbnoSide lethal(false);
    assert(lethal.Join("one") && lethal.Join("two") && lethal.Join("three"));
    assert(lethal.Down("one",1)==InvaderEvent::Disconnected);
    assert(!lethal.Ended() && lethal.ConnectedCount()==2 && lethal.DownCount()==0);
    assert(!lethal.Join("one")); // stale rejoin blocked by tombstone
    assert(lethal.Down("two",1)==InvaderEvent::Disconnected);
    assert(lethal.ConnectedCount()==1 && !lethal.Ended());
    assert(lethal.Down("three",1)==InvaderEvent::SideDefeated);
    assert(lethal.Ended() && lethal.ConnectedCount()==0);
    // A living invader disconnecting while the rest are down terminates the side.
    InvaderDbnoSide partial(true);
    assert(partial.Join("a") && partial.Join("b") && partial.Join("c"));
    assert(partial.Down("a",4)==InvaderEvent::Downed);
    assert(partial.Down("b",8)==InvaderEvent::Downed);
    assert(partial.Disconnect("c",9)==InvaderEvent::SideDefeated);
    assert(partial.Ended() && partial.ConnectedCount()==0);
    // A solo invader cannot remain downed forever with nobody to revive them.
    InvaderDbnoSide solo(true);
    assert(solo.Join("lonely"));
    assert(solo.Down("lonely",3)==InvaderEvent::SideDefeated);
    // Revive requires a living invader, not an opposing cooperative hunter.
    InvaderDbnoSide duo(true);
    assert(duo.Join("a") && duo.Join("b"));
    assert(duo.Down("a",8)==InvaderEvent::Downed);
    assert(duo.Revive("a","not-in-party",9)==InvaderEvent::Ignored);
    assert(duo.Disconnect("a",9)==InvaderEvent::Disconnected);
    assert(duo.AliveCount()==1 && !duo.Ended());
    assert(duo.Disconnect("b",1)==InvaderEvent::SideDefeated);
    std::cout<<"PASS: three-hostile DBNO revive, final defeat, opt-out, disconnects and stale events\n";
}
