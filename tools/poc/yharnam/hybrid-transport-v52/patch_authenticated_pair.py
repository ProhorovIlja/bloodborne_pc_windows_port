#!/usr/bin/env python3
"""V66 pinned shadNet Hub admission: server-owned pair eligibility, fail closed.

This modifies real server/src/server_link.{h,cpp} and the native Qt server
test_server_link.cpp. It does NOT transmit a grant, endpoint, token or key.
Runtime game offload is forbidden until mutual opt-in, authenticated secure
rendezvous, key establishment and safe GameLink stream switching all exist.
"""
from __future__ import annotations

from pathlib import Path

HEADER="server/src/server_link.h"
SOURCE="server/src/server_link.cpp"
TEST="server/tests/test_server_link.cpp"


def replace_exact(src: str, before: str, after: str, description: str) -> str:
    if src.count(before) != 1:
        raise ValueError(f"pinned upstream {description} missing or duplicated")
    return src.replace(before, after, 1)


def transform(files: dict[str, str]) -> dict[str, str]:
    if set(files) != {HEADER, SOURCE, TEST}:
        raise ValueError("exact pinned Hub headers, code and tests required")
    h, cpp, test = (files[p] for p in (HEADER, SOURCE, TEST))
    if "DirectPairEligible" in h or "DirectPairEligible" in cpp or "DirectPairEligible" in test:
        raise ValueError("already patched; no double application")

    h = replace_exact(h,
'''    int Members() const {
''',
'''    // Only the authenticated server MAY install the consent resolver.
    // It must read both players' server-owned session opt-ins, not user JSON.
    // With no resolver, no sign-in callback or no group callback, this
    // read-only pre-grant gate fails closed and discloses NO real endpoints.
    using DirectConsent = std::function<bool(const QByteArray&, const QByteArray&)>;
    void SetDirectConsent(DirectConsent resolver) {
        direct_consent = std::move(resolver);
    }
    bool DirectPairEligible(const Endpoint& source, const Endpoint& destination,
                            qint64 now_ms) const;

    int Members() const {
''',"Hub public pair gate")
    h = replace_exact(h,
'''    SignIn sign_in;
''',
'''    SignIn sign_in;
    DirectConsent direct_consent; // unconfigured in production => no P2P grant
''',"Hub private resolver")

    # V68: preserve sign-in provenance at the ORIGINAL successful Hello.
    h = replace_exact(h,
'''        qint64 last_heard_ms = 0;
''',
'''        qint64 last_heard_ms = 0;
        bool authenticated_at_hello = false;
''',"explicit login marker")
    cpp = replace_exact(cpp,
'''Hub::Result Hub::Receive(const Endpoint& from, const QByteArray& datagram, qint64 now_ms) {
''',
'''// V66: operate on AUTHENTICATED shadNet Hello links and server-owned team
// membership before any future candidate/key exchange. This never creates
// a grant or returns actual socket addresses to a game/client.
bool Hub::DirectPairEligible(const Endpoint& source, const Endpoint& destination,
                             qint64 now_ms) const {
    if (!sign_in || !party_of || !direct_consent || source == destination ||
        now_ms < 0 || quiet_ms <= 0)
        return false;
    const auto one = members.constFind(source.Key());
    const auto two = members.constFind(destination.Key());
    if (one == members.cend() || two == members.cend())
        return false;
    const Link& a = *one;
    const Link& b = *two;
    if (a.online_id.isEmpty() || b.online_id.isEmpty() ||
        a.online_id == b.online_id || a.build.isEmpty() || b.build.isEmpty() ||
        a.build != b.build || !a.authenticated_at_hello ||
        !b.authenticated_at_hello || a.quiet || b.quiet || a.lost || b.lost ||
        now_ms < a.last_heard_ms || now_ms < b.last_heard_ms ||
        now_ms - a.last_heard_ms > quiet_ms ||
        now_ms - b.last_heard_ms > quiet_ms ||
        !SameTeam(source, destination))
        return false;
    // Read both DIRECTIONS of consent; no default implicit consent for
    // friends, members, invaders, old clients, or lobby visibility.
    return direct_consent(a.online_id, b.online_id) &&
           direct_consent(b.online_id, a.online_id);
}

Hub::Result Hub::Receive(const Endpoint& from, const QByteArray& datagram, qint64 now_ms) {
''',"Hub pair authorization implementation")

    cpp = replace_exact(cpp,
'''    link.last_heard_ms = now_ms;
''',
'''    link.last_heard_ms = now_ms;
    // SignIn above must have succeeded for THIS specific accepted Hello.
    link.authenticated_at_hello = static_cast<bool>(sign_in);
''',"per-hello authentication provenance")

    test = replace_exact(test,
'''int HelloAndBuilds() {
''',
'''int DirectPairAdmission() {
  Hub hub;
  const auto allows_sign_in = [](const QByteArray& user, const QByteArray& secret) {
    return !user.isEmpty() && secret == "test-only-password";
  };
  const auto both_in_party = [](const Endpoint& member) -> QString {
    if (member == Kaniel || member == Ada) return "same-team";
    return "another-team";
  };
  // No client opt-ins or P2P feature by default, even with valid Hellos.
  hub.SetSignIn(allows_sign_in);
  hub.SetPartyOf(both_in_party);
  hub.Receive(Kaniel, HelloFrom("Kaniel", Build, "test-only-password"), 0);
  hub.Receive(Ada, HelloFrom("Ada", Build, "test-only-password"), 0);
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 1));
  hub.SetDirectConsent([](const QByteArray&, const QByteArray&) { return false; });
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 1));
  hub.SetDirectConsent([](const QByteArray& a, const QByteArray& b) {
    return a == "Kaniel" && b == "Ada"; // unilateral opt-in insufficient
  });
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 1));
  hub.SetDirectConsent([](const QByteArray& a, const QByteArray& b) {
    return (a == "Kaniel" && b == "Ada") ||
           (a == "Ada" && b == "Kaniel");
  });
  CHECK(hub.DirectPairEligible(Kaniel, Ada, 1));
  CHECK(hub.DirectPairEligible(Ada, Kaniel, 1));
  CHECK(!hub.DirectPairEligible(Kaniel, Kaniel, 1));
  CHECK(!hub.DirectPairEligible(Kaniel, Eileen, 1));
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, -1));
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 3001)); // stale heartbeat

  hub.Receive(Ada, Encode(Kind::Ping, Ping{1, 3001}), 3001);
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 3001)); // still stale peer
  hub.Receive(Kaniel, Encode(Kind::Ping, Ping{1, 3002}), 3002);
  CHECK(hub.DirectPairEligible(Kaniel, Ada, 3002));
  // Session rebinding/changed build must invalidate previous direct grant.
  hub.Receive(Ada, HelloFrom("Ada", "", "test-only-password"), 3003);
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 3003));
  hub.Receive(Ada, HelloFrom("Ada", Build, "test-only-password"), 3004);
  CHECK(hub.DirectPairEligible(Kaniel, Ada, 3004));
  hub.SetPartyOf([](const Endpoint&) -> QString { return {}; });
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 3005));
  hub.SetPartyOf([&](const Endpoint& e) -> QString {
    return e == Kaniel ? "room-1" : "room-2";
  });
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 3006));
  hub.SetPartyOf(both_in_party);
  hub.SetDirectConsent({});
  CHECK(!hub.DirectPairEligible(Kaniel, Ada, 3007));

  // Auth callback and group callback are mandatory, not merely two Hellos.
  Hub no_auth;
  no_auth.SetPartyOf(both_in_party);
  no_auth.SetDirectConsent([](auto, auto) { return true; });
  no_auth.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  no_auth.Receive(Ada, HelloFrom("Ada"), 0);
  CHECK(!no_auth.DirectPairEligible(Kaniel, Ada, 1));
  Hub no_party;
  no_party.SetSignIn(allows_sign_in);
  no_party.SetDirectConsent([](auto, auto) { return true; });
  no_party.Receive(Kaniel, HelloFrom("Kaniel", Build, "test-only-password"), 0);
  no_party.Receive(Ada, HelloFrom("Ada", Build, "test-only-password"), 0);
  CHECK(!no_party.DirectPairEligible(Kaniel, Ada, 1));
  // V68: callback installed after old unauthenticated Hellos is not retroactive.
  Hub late_auth;
  late_auth.SetPartyOf(both_in_party);
  late_auth.SetDirectConsent([](auto, auto) { return true; });
  late_auth.Receive(Kaniel, HelloFrom("Kaniel", Build), 0);
  late_auth.Receive(Ada, HelloFrom("Ada", Build), 0);
  late_auth.SetSignIn(allows_sign_in);
  CHECK(!late_auth.DirectPairEligible(Kaniel, Ada, 1));
  late_auth.Receive(Kaniel, HelloFrom("Kaniel", Build, "test-only-password"), 2);
  CHECK(!late_auth.DirectPairEligible(Kaniel, Ada, 3));
  late_auth.Receive(Ada, HelloFrom("Ada", Build, "test-only-password"), 4);
  CHECK(late_auth.DirectPairEligible(Kaniel, Ada, 5));
  Hub failed_login;
  failed_login.SetSignIn(allows_sign_in);
  failed_login.SetPartyOf(both_in_party);
  failed_login.SetDirectConsent([](auto,auto){return true;});
  failed_login.Receive(Kaniel,HelloFrom("Kaniel",Build,"wrong"),0);
  failed_login.Receive(Ada,HelloFrom("Ada",Build,"test-only-password"),0);
  CHECK(!failed_login.DirectPairEligible(Kaniel,Ada,1));

  // A forged/rejected Hello must not register a link.
  const Endpoint attacker{0x7F000001, 40009};
  hub.Receive(attacker, HelloFrom("attacker", Build, "wrong"), 3008);
  CHECK(!hub.DirectPairEligible(attacker, Ada, 3009));
  std::cout << "direct candidate admission: ok\\n";
  return 0;
}

int HelloAndBuilds() {
''',"native server link pair regression")
    test = replace_exact(test,
'''HelloAndBuilds() != 0 ||''',
'''HelloAndBuilds() != 0 || DirectPairAdmission() != 0 ||''',"native server test invocation")
    return {HEADER:h,SOURCE:cpp,TEST:test}


def apply_to_checkout(root: Path) -> None:
    # Preflight ALL files before writing ANY: never half-apply to a build.
    old={p:(root/p).read_text("utf-8") for p in (HEADER,SOURCE,TEST)}
    new=transform(old)
    for p,v in new.items():
        (root/p).write_text(v,"utf-8")


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("pinned_checkout",type=Path)
    args=p.parse_args()
    apply_to_checkout(args.pinned_checkout)
    print("SHYT_V66_REAL_SHADNET_PAIR_ADMISSION_PATCH_PASS")
