#!/usr/bin/env python3
"""V78 optional mutual TLS 1.3 loopback-only Qt rendezvous listener.

The one existing Qt shadNet process owns this listener. Disabled unless
SHYT_P2P_TLS_LOCAL_TEST=1, never discloses IPs/tokens, never issues grants.
"""
from __future__ import annotations
MAIN="server/src/main.cpp"
HEADER="server/src/sh_p2p_tls_listener.hpp"
def patch(main: str) -> str:
    if "SHYT_P2P_TLS_LOCAL_TEST" in main:
        raise ValueError("V78 applied twice")
    inc='#include "webapi_server.h"\n'
    if main.count(inc)!=1: raise ValueError("V78 original main header drift")
    main=main.replace(inc,inc+'#include "sh_p2p_tls_listener.hpp" // V78 secure local rendezvous\n',1)
    anchor='''    // Start the HTTP/JSON WebAPI listener alongside the binary protocol.
'''
    replacement='''    // V78: optional TLS 1.3 mTLS loopback PROBE in THIS shadNet daemon.
    // Disabled by default. Never expose on a public interface or use the
    // existing plaintext SHLK/HTTP for ephemeral P2P credentials. We do
    // not have cert-to-current-game-account binding or a grant issuer yet.
    SeamlessHunt::Hybrid::P2PTlsListener p2p_tls;
    if (qEnvironmentVariable("SHYT_P2P_TLS_LOCAL_TEST")=="1") {
        bool port_ok=false;
        const auto configured_port=qEnvironmentVariable("SHYT_P2P_TLS_LOCAL_PORT");
        const quint16 port=configured_port.isEmpty() ? 0 :
            configured_port.toUShort(&port_ok);
        if ((!configured_port.isEmpty() && !port_ok) ||
            !p2p_tls.StartLocal(
                qEnvironmentVariable("SHYT_P2P_TLS_SERVER_CERT"),
                qEnvironmentVariable("SHYT_P2P_TLS_SERVER_KEY"),
                qEnvironmentVariable("SHYT_P2P_TLS_CLIENT_CA"),port)) {
            qCritical() << "P2P TLS local test was explicitly enabled but "
                           "TLS 1.3/certificate configuration failed";
            return 1; // never downgrade or silently run a plain listener
        }
        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
                << p2p_tls.serverPort() << "(no grants supported)";
    }

    // Start the HTTP/JSON WebAPI listener alongside the binary protocol.
'''
    if main.count(anchor)!=1: raise ValueError("V78 main startup anchor drift")
    return main.replace(anchor,replacement,1)
