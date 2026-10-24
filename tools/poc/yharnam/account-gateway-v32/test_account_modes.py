import unittest
from account_modes import Mode, Credentials, may_enter

class AccountModes(unittest.TestCase):
    def test_solo_direct_legacy_never_regressed(self):
        for mode in (Mode.SOLO, Mode.DIRECT_PARTY, Mode.LEGACY_CLS):
            with self.subTest(mode=mode):
                result = may_enter(mode, Credentials())
                self.assertTrue(result.allowed)
                self.assertFalse(result.requires_account)
    def test_public_server_requires_all_four_conditions(self):
        all_ok=Credentials(True,True,True,True)
        self.assertTrue(may_enter(Mode.PUBLIC_REALM,all_ok).allowed)
        for key in ("identity_confirmed","realm_reachable",
                    "admission_ticket_confirmed_by_server","compatible_client"):
            kwargs=dict(identity_confirmed=True,realm_reachable=True,
                        admission_ticket_confirmed_by_server=True,compatible_client=True)
            kwargs[key]=False
            with self.subTest(key=key):
                self.assertFalse(may_enter(Mode.PUBLIC_REALM,Credentials(**kwargs)).allowed)
    def test_no_local_server_required_for_public_realm(self):
        proof=Credentials(True,True,True,True)
        self.assertTrue(may_enter(Mode.PUBLIC_REALM,proof).allowed)
    def test_private_server_explicit_policy(self):
        c=Credentials(False,True,False,True)
        self.assertTrue(may_enter(Mode.PRIVATE_REALM,c,private_requires_account=False).allowed)
        self.assertFalse(may_enter(Mode.PRIVATE_REALM,c,private_requires_account=True).allowed)
    def test_realm_unavailable_does_not_disable_offline(self):
        for mode in (Mode.PUBLIC_REALM,Mode.PRIVATE_REALM):
            self.assertFalse(may_enter(mode,Credentials()).allowed)
        self.assertTrue(may_enter(Mode.SOLO,Credentials()).allowed)
if __name__=="__main__":unittest.main()
