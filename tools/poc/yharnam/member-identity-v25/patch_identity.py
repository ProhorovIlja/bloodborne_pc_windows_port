#!/usr/bin/env python3
"""V25 identity bridge between logged-in transport and co-op envelope, opt in."""
from pathlib import Path
WORLD='server/src/bloodborne_world.cpp'
LINK='server/src/server_link.cpp'
HEADER='server/src/sh_member_identity.hpp'
HERE=Path(__file__).resolve().parent
def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise ValueError(f'V25 {label}: expected exactly 1 source anchor; found {n}')
    return s.replace(old,new,1)
def patch_world(s):
    if 'SH-MEMBER-ID-V25' in s:raise ValueError('V25 already applied')
    s=one(s,'#include "bloodborne_world.h"',
        '#include "bloodborne_world.h"\n#include "sh_member_identity.hpp" // SH-MEMBER-ID-V25','world header')
    s=one(s,
        '''    // The same run saying hello again (a guest whose game took the session host's role: phase 7).''',
        '''    // In strict rooms, the game cannot impersonate a different member just
    // by changing Hello.member: this is derived from authenticated link ID.
    if (SeamlessHunt::Identity::StrictMode() &&
        !SeamlessHunt::Identity::Matches(
            std::string_view(member.online_id.constData(), std::size_t(member.online_id.size())),
            hello.member())) {
        bbcoop::Envelope refuse;
        refuse.mutable_welcome()->set_text("co-op identity does not match signed-in account");
        SendTo(member, refuse, now_ms);
        return;
    }
    // The same run saying hello again (a guest whose game took the session host's role: phase 7).''',
        'party member claim')
    s=one(s,
        '''    const bool arrived = member.lobby.empty();''',
        '''    if (SeamlessHunt::Identity::StrictMode() &&
        !SeamlessHunt::Identity::Matches(
            std::string_view(member.online_id.constData(), std::size_t(member.online_id.size())),
            hello.member())) {
        bbcoop::Envelope refuse;
        refuse.mutable_lobby_state()->set_notice("lobby identity does not match signed-in account");
        SendTo(member, refuse, now_ms);
        return;
    }
    const bool arrived = member.lobby.empty();''',
        'lobby member claim')
    return s
def patch_link(s):
    if 'SH-MEMBER-ID-V25' in s:raise ValueError('V25 already applied')
    s=one(s, '#include "server_link.h"',
        '#include "server_link.h"\n#include "sh_member_identity.hpp" // SH-MEMBER-ID-V25',
        'server link header')
    s=one(s,
        '''    if (refusal.isEmpty() && sign_in && !sign_in(hello->online_id, hello->secret)) {''',
        '''    // A strict room MUST configure real SignIn verification. Merely
    // matching two client-supplied strings is not authentication.
    if (refusal.isEmpty() && SeamlessHunt::Identity::StrictMode() && !sign_in) {
        refusal = "strict identity mode requires authenticated sign-in";
    }
    if (refusal.isEmpty() && sign_in && !sign_in(hello->online_id, hello->secret)) {''',
        'strict auth prerequisite')
    return s
def transform(sources):
    return {WORLD:patch_world(sources[WORLD]),LINK:patch_link(sources[LINK]),
            HEADER:(HERE/'sh_member_identity.hpp').read_text('utf8')}
