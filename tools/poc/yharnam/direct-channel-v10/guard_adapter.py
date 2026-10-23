#!/usr/bin/env python3
"""Add a strict Pass-only native gameplay channel gate to archived V7's adapter.
Server-dependent/map-dependent native packets still take the original relay.
No authenticated shadNet rendezvous or player release is claimed here.
"""
def replace_once(text, old, new, label):
    found=text.count(old)
    if found!=1:raise ValueError(f"{label}: expected one V7 anchor, found {found}")
    return text.replace(old,new,1)
def patch_adapter(source):
    if "DirectSafeGameFrame" in source or '"native_direct_filter.hpp"' in source:
        raise ValueError("V10 guard already installed")
    source=replace_once(source,
        '#include "native_shlk_direct.hpp"',
        '#include "native_shlk_direct.hpp"\n#include "native_direct_filter.hpp"',
        'include')
    source=replace_once(source,
        '  std::optional<WireSend> TryGame(Endpoint virtual_dest,std::span<const std::uint8_t> frame,std::int64_t now) {\n    std::scoped_lock lock(mu_);',
        '  std::optional<WireSend> TryGame(Endpoint virtual_dest,std::span<const std::uint8_t> frame,std::int64_t now) {\n    if (!DirectSafeGameFrame(frame)) return {}; // preserve shadNet server channel policy\n    std::scoped_lock lock(mu_);',
        'outbound')
    source=replace_once(source,
        '      out.data=std::move(received);',
        '      if (received && DirectSafeGameFrame(received->game_frame))\n        out.data=std::move(received); // no signed peer frame bypasses channel filtering',
        'inbound')
    return source
