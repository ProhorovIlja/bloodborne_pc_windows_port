import unittest
from patch_rpc_budget import patch_cpp,patch_header
CPP='''    m_signedIn.insert(online_id, hash);
    return true;
        case Kind::Opened:
            OpenRpc(online_id, end);
            break;
        case Kind::Data: {
            const QByteArray data(reinterpret_cast<const char*>(event.bytes.data()),
                                  static_cast<qsizetype>(event.bytes.size()));
            if (end.socket && end.socket->state() == QAbstractSocket::ConnectedState)
                end.socket->write(data);
            else
                end.pending.append(data);
            break;
        }'''
H='''#include <map>
        QByteArray pending; // what came before the connection to the TCP port was up'''
class Tests(unittest.TestCase):
    def test_cache_is_bounded(self):
        s=patch_cpp(CPP)
        self.assertLess(s.index('MustEvictAuthCache('),s.index('m_signedIn.insert('))
        self.assertIn('m_signedIn.erase(m_signedIn.begin())',s)
    def test_rpc_queue_is_checked_before_allocations(self):
        s=patch_cpp(CPP)
        self.assertLess(s.index('RpcBudget::Fits(pending, bytes)'),s.index('const QByteArray data'))
        self.assertIn('end.blocked = true;',s)
        self.assertIn('end.tunnel->Close(',s)
        self.assertIn('end.socket->bytesToWrite()',s)
        self.assertIn('end.blocked = false;',s)
    def test_block_flag_lives_with_rpc_session(self):
        self.assertIn('bool blocked = false;',patch_header(H))
    def test_reject_changed_source(self):
        with self.assertRaisesRegex(ValueError,'bounded rpc data and socket write'):
            patch_cpp(CPP.replace('end.pending.append(data)','end.pending.push_back(data)'))
    def test_double_apply_rejected(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            patch_cpp(patch_cpp(CPP))
if __name__=='__main__':unittest.main()
