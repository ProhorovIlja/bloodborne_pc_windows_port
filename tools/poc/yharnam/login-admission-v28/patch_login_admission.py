#!/usr/bin/env python3
"""V28: reject login floods before Hub calls expensive DB-backed SignIn."""
from pathlib import Path

LINK_CPP = 'server/src/server_link.cpp'
LINK_H = 'server/src/server_link.h'
QT_TEST = 'server/tests/test_server_link.cpp'
HEADER = 'server/src/sh_login_admission.hpp'
HERE = Path(__file__).resolve().parent

def one(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise ValueError(f'V28 {label}: expected exactly one pinned source anchor, got {n}')
    return s.replace(old, new, 1)

def patch_link_cpp(s):
    if 'SH-LOGIN-ADMISSION-V28' in s:
        raise ValueError('V28 already applied to Hub implementation')
    return one(s, '''    const auto hello = DecodeHello(datagram);
    if (!hello) {
        return;
    }
    QByteArray refusal;''', '''    const auto hello = DecodeHello(datagram);
    if (!hello) {
        return;
    }
    // SH-LOGIN-ADMISSION-V28: cheap, bounded work before any password DB/KDF.
    // Silent rejection is intentional: ordinary clients retry Hello, and a
    // Welcome refusal could cause a permanent login failure.
    if (SeamlessHunt::LoginAdmission::Enabled() &&
        !hello_admission.Allow(from.ipv4, now_ms)) {
        return;
    }
    QByteArray refusal;''', 'before SignIn')

def patch_link_h(s):
    if 'SH-LOGIN-ADMISSION-V28' in s:
        raise ValueError('V28 already applied to Hub header')
    s = one(s, '#include <map>', '#include <map>\n#include "sh_login_admission.hpp" // SH-LOGIN-ADMISSION-V28', 'policy include')
    return one(s, '''    int pair_lines;''', '''    int pair_lines;
    // Fixed-size 4-way IP table and global token bucket, never allocates per
    // untrusted Hello. Disabled unless SH_LOGIN_ADMISSION=1.
    SeamlessHunt::LoginAdmission::Gate hello_admission;''', 'Hub budget')

def patch_test(s):
    if 'SH-LOGIN-ADMISSION-V28' in s:
        raise ValueError('V28 already applied to Qt tests')
    s = one(s, 'int Relays() {', '''// SH-LOGIN-ADMISSION-V28: first-hop flood test exercises real Hub::OnHello.
int HelloAdmissionLimitsDbCalls() {
  qputenv("SH_LOGIN_ADMISSION", "1");
  Hub hub;
  int sign_in_calls = 0;
  hub.SetSignIn([&](const QByteArray&, const QByteArray&) {
    ++sign_in_calls;
    return true;
  });
  for (int i = 0; i < 40; ++i) {
    const auto result = hub.Receive(
        {Kaniel.ipv4, static_cast<quint16>(30000 + i)},
        HelloFrom("Kaniel"), 10);
    (void)result;
  }
  CHECK(sign_in_calls == static_cast<int>(SeamlessHunt::LoginAdmission::Gate::IpBurst));
  hub.Receive({Kaniel.ipv4, 40000}, HelloFrom("Kaniel"), 510);
  CHECK(sign_in_calls == 9);
  qunsetenv("SH_LOGIN_ADMISSION");
  std::cout << "login admission rate gate: ok\\n";
  return 0;
}

int Relays() {''', 'Qt Hub flood regression')
    return one(s, '''      ChangedAccountOnSameEndpoint() != 0 || Relays() != 0 ||''',
        '''      ChangedAccountOnSameEndpoint() != 0 ||
      HelloAdmissionLimitsDbCalls() != 0 || Relays() != 0 ||''', 'Qt test runner')

def transform(sources):
    return {LINK_CPP: patch_link_cpp(sources[LINK_CPP]),
            LINK_H: patch_link_h(sources[LINK_H]),
            QT_TEST: patch_test(sources[QT_TEST]),
            HEADER: (HERE/'sh_login_admission.hpp').read_text('utf-8')}
