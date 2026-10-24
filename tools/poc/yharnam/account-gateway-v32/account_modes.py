"""Launcher UX policy, not server authorization. Never grants network access."""
from dataclasses import dataclass
from enum import Enum

class Mode(str, Enum):
    SOLO = "solo"
    DIRECT_PARTY = "direct-party"
    LEGACY_CLS = "legacy-cls"
    PUBLIC_REALM = "public-realm"
    PRIVATE_REALM = "private-realm"

@dataclass(frozen=True)
class Credentials:
    identity_confirmed: bool = False
    realm_reachable: bool = False
    admission_ticket_confirmed_by_server: bool = False
    compatible_client: bool = False

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    requires_account: bool

def may_enter(mode: Mode, proof: Credentials, *, private_requires_account: bool = True) -> Decision:
    """UX-only policy. Never trust the launcher as a security boundary.

    True server-side acceptance MUST validate TLS-bound short-lived signed
    tickets and one-time challenge/nonce. A local setting or this result never
    overrides the server.
    """
    if mode in (Mode.SOLO, Mode.DIRECT_PARTY, Mode.LEGACY_CLS):
        return Decision(True, "No Seamless Hunt account required in this mode.", False)
    needs_account = mode is Mode.PUBLIC_REALM or private_requires_account
    if not proof.realm_reachable:
        return Decision(False, "Selected realm unavailable; solo/direct play still works.", needs_account)
    if not proof.compatible_client:
        return Decision(False, "This native client does not support the selected realm yet.", needs_account)
    if needs_account and not proof.identity_confirmed:
        return Decision(False, "Sign in through the account website first.", True)
    if needs_account and not proof.admission_ticket_confirmed_by_server:
        return Decision(False, "Game admission ticket not confirmed by the realm.", True)
    return Decision(True, "The realm may accept this client subject to its own checks.", needs_account)
