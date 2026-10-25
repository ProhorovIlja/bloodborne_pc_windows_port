#!/usr/bin/env python3
"""V82: pin-sensitive original native Yharnam Together game inbox owner.

No TLS connection/client implementation yet, and no native Arm() call.
Only store an UNARMED verified-offer inbox on the real P2PTransport object
and revoke it with original SHLK transport/account lifecycle.
"""
from __future__ import annotations
NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="emulator/src/core/libraries/network/sh_native_grant_inbox.hpp"

def one(s,a,b,label):
    n=s.count(a)
    if n!=1:raise ValueError(f"V82 {label}: expected exact one original game anchor, found {n}")
    return s.replace(a,b,1)

def patch_game(src):
    if "SHYT-V82-NATIVE-GRANT-INBOX" in src:
        raise ValueError("V82 native grant already integrated")
    src=one(src,
'''#include "core/libraries/network/sh_native_direct_tx.hpp" // SHYT-V71-NATIVE-DIRECT-TX
''',
'''#include "core/libraries/network/sh_native_direct_tx.hpp" // SHYT-V71-NATIVE-DIRECT-TX
#include "core/libraries/network/sh_native_grant_inbox.hpp" // SHYT-V82-NATIVE-GRANT-INBOX
''',"original P2PTransport native include")
    src=one(src,
'''    SeamlessHunt::Hybrid::NativeDirectSender direct_egress{};
''',
'''    SeamlessHunt::Hybrid::NativeDirectSender direct_egress{};
    // V82: pending AES-GCM grant belongs to THIS game's live server account
    // and native transport, not an independent daemon or launcher process.
    // No TLS-provisioned key/caller exists; default state is inert/deny.
    std::mutex native_grant_mutex;
    SeamlessHunt::Hybrid::NativeSealedGrantInbox native_grant_inbox{};
''',"actual native game session owns secure grant inbox")
    src=one(src,
'''            direct_egress.RevokeAll();
        }
#endif
''',
'''            direct_egress.RevokeAll();
        }
        {
            std::lock_guard grant_lock(native_grant_mutex);
            native_grant_inbox.Revoke(); // socket shutdown: erase key & peer
        }
#endif
''',"existing network stop invalidates session-bound offer")
    src=one(src,
'''            direct_egress.RevokeAll();
        }
        LOG_INFO(Lib_Net, "Server link: every frame for a peer goes through the server at {:#x}:{}",
''',
'''            direct_egress.RevokeAll();
        }
        {
            std::lock_guard grant_lock(native_grant_mutex);
            native_grant_inbox.Revoke(); // account/server change: invalidate
        }
        LOG_INFO(Lib_Net, "Server link: every frame for a peer goes through the server at {:#x}:{}",
''',"original server link replacement invalidates offer")
    return src
