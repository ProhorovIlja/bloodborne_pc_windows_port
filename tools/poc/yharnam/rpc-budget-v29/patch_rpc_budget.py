#!/usr/bin/env python3
"""V29: cap local RPC TCP queues and signed-in credential cache entries."""
from pathlib import Path
LINK = 'server/src/link_server.cpp'
HEADER = 'server/src/link_server.h'
GUARD = 'server/src/sh_rpc_budget.hpp'
HERE = Path(__file__).resolve().parent

def one(s, old, new, label):
    n=s.count(old)
    if n!=1: raise ValueError(f'V29 {label}: expected one source anchor, found {n}')
    return s.replace(old,new,1)

def patch_header(s):
    if 'SH-RPC-BUDGET-V29' in s: raise ValueError('V29 already applied to header')
    s=one(s, '#include <map>', '#include <map>\n#include "sh_rpc_budget.hpp" // SH-RPC-BUDGET-V29', 'header include')
    return one(s, '''        QByteArray pending; // what came before the connection to the TCP port was up''',
      '''        QByteArray pending; // what came before the connection to the TCP port was up
        // Stop consuming a flooded RPC tunnel until its next genuine Opened event.
        bool blocked = false;''', 'per-tunnel blocked state')

def patch_cpp(s):
    if 'SH-RPC-BUDGET-V29' in s: raise ValueError('V29 already applied to cpp')
    s=one(s,
      '''    m_signedIn.insert(online_id, hash);
    return true;''',
      '''    // SH-RPC-BUDGET-V29: prevent indefinite growth under account churn.
    // A cache eviction only forces normal database verification on next sign-in.
    if (SeamlessHunt::RpcBudget::MustEvictAuthCache(std::size_t(m_signedIn.size())))
        m_signedIn.erase(m_signedIn.begin());
    m_signedIn.insert(online_id, hash);
    return true;''', 'bounded cached accounts')
    s=one(s,
      '''        case Kind::Opened:
            OpenRpc(online_id, end);
            break;''',
      '''        case Kind::Opened:
            end.blocked = false; // a new tunnel opens after previous overflow
            OpenRpc(online_id, end);
            break;''', 'rpc new tunnel recovery')
    s=one(s,
      '''        case Kind::Data: {
            const QByteArray data(reinterpret_cast<const char*>(event.bytes.data()),
                                  static_cast<qsizetype>(event.bytes.size()));
            if (end.socket && end.socket->state() == QAbstractSocket::ConnectedState)
                end.socket->write(data);
            else
                end.pending.append(data);
            break;
        }''',
      '''        case Kind::Data: {
            // Guard BOTH queues: before TCP connects and when Qt's socket
            // cannot drain. Bound work before copying the incoming payload.
            if (end.blocked) break;
            const auto bytes = event.bytes.size();
            const auto pending = end.socket &&
                     end.socket->state() == QAbstractSocket::ConnectedState
                ? static_cast<std::size_t>(std::max<qint64>(0, end.socket->bytesToWrite()))
                : static_cast<std::size_t>(end.pending.size());
            if (!SeamlessHunt::RpcBudget::Fits(pending, bytes)) {
                end.blocked = true;
                CloseRpc(end);
                end.tunnel->Close(m_clock.elapsed());
                break;
            }
            const QByteArray data(reinterpret_cast<const char*>(event.bytes.data()),
                                  static_cast<qsizetype>(bytes));
            if (end.socket && end.socket->state() == QAbstractSocket::ConnectedState)
                end.socket->write(data);
            else
                end.pending.append(data);
            break;
        }''', 'bounded rpc data and socket write')
    return s

def transform(sources):
    return {LINK:patch_cpp(sources[LINK]),
            HEADER:patch_header(sources[HEADER]),
            GUARD:(HERE/'sh_rpc_budget.hpp').read_text('utf-8')}
