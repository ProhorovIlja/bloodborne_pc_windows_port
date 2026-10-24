#!/usr/bin/env python3
"""V57 explicit non-credential TCP server diagnostics for original BLauncher.

Only used after the player clicks Test server. Never logs passwords, sends
tokens, touches production Fornex services automatically, or claims UDP
matching, Direct P2P, gameplay authentication or health was verified.
"""
from __future__ import annotations

HELPER = '''# SHYT_LAUNCHER_TCP_DIAG_V57
def shyt_tcp_backend_probe(coop_module, install, ip):
    # This performs two bounded TCP connects and nothing else. Do not report
    # network game's UDP reachability or user account sign-in from this data.
    ports = coop_module.shyt_remote_ports(install, ip)
    backend = coop_module.port_open(ports['backend_tcp_port'], ip, timeout=1.0)
    webapi = coop_module.port_open(ports['webapi_tcp_port'], ip, timeout=1.0)
    return bool(backend), bool(webapi)


'''


def exactly(s: str, old: str, new: str, field: str) -> str:
    n = s.count(old)
    if n != 1:
        raise ValueError(f"V57 original BLauncher source drift ({field}): {n}")
    return s.replace(old, new, 1)


def transform(src: str) -> str:
    if "SHYT_LAUNCHER_TCP_DIAG_V57" in src:
        raise ValueError("V57 launcher probe already present")
    if "SHYT_LAUNCHER_ONBOARDING_V56" not in src:
        raise ValueError("V57 must follow V56 original BLauncher onboarding")
    src = HELPER + src
    anchor = """        self.note(card, _('Create or join co-op teams inside the Yharnam Together game. '"""
    button = """        # A manual network diagnostic, never a speculative green Online badge.
        # TCP sockets are tested only on click; no accounts or gameplay packets.
        probe = tk.Frame(card, bg=CARD)
        probe.grid(row=self.next_row(card), column=0, columnspan=2,
                   sticky='we', pady=(px(8), 0))
        self.coop_probe_button = self.button(
            probe, _('Test server TCP', 'Проверить TCP сервера'),
            self.coop_probe_server, bg=CARD)
        self.coop_probe_button.pack(side='left')
        self.coop_probe_line = self.label(
            probe,
            _('TCP-only check. UDP matchmaking and Direct P2P not tested.',
              'Проверяется только TCP. UDP-матчмейкинг и Direct P2P не проверяются.'),
            'small', MUTED, bg=CARD, anchor='w')
        self.coop_probe_line.pack(side='left', padx=(px(12), 0), fill='x',
                                  expand=True)
""" + anchor
    src = exactly(src, anchor, button, "TCP-only diagnostic field")
    new_method = """    def coop_probe_server(self):
        \"\"\"One opt-in non-credential TCP test; no false network-ready claim.\"\"\"
        if getattr(self, 'coop_probe_pending', False):
            return
        ip = self.coop_vars['host_ip'].get().strip()
        if not bbport_coop.valid_ip(ip):
            self.coop_probe_line.configure(
                text=_('Enter a valid server IPv4 first.',
                       'Сначала введите правильный IPv4 сервера.'), fg=CAUTION)
            return
        self.coop_probe_pending = True
        self.coop_probe_button.configure(state='disabled')
        self.coop_probe_line.configure(
            text=_('Checking backend and WebAPI TCP…',
                   'Проверка TCP сервера игры и WebAPI…'), fg=MUTED)

        def work():
            try:
                backend, webapi = shyt_tcp_backend_probe(bbport_coop, PORT_DIR, ip)
                if backend and webapi:
                    result, color = _(
                        'Backend and WebAPI TCP reachable. UDP / Direct P2P still untested.',
                        'TCP сервера игры и WebAPI доступны. UDP / Direct P2P не проверены.'), OK
                elif not backend and not webapi:
                    result, color = _(
                        'Backend and WebAPI TCP are unreachable.',
                        'Сервер игры и WebAPI по TCP недоступны.'), CAUTION
                elif not backend:
                    result, color = _(
                        'Backend TCP unreachable; WebAPI TCP reachable.',
                        'TCP сервера игры недоступен; WebAPI доступен.'), CAUTION
                else:
                    result, color = _(
                        'Backend TCP reachable; WebAPI TCP unreachable.',
                        'TCP сервера игры доступен; WebAPI недоступен.'), CAUTION
            except Exception:
                # A worker failure must never strand the UI in a disabled state.
                # Keep exception details (possibly containing private paths) out of the UI.
                result, color = _(
                    'Server test configuration invalid. Check the selected profile.',
                    'Ошибка конфигурации. Проверьте профиль сервера.'), CAUTION

            def display():
                self.coop_probe_pending = False
                if not hasattr(self, 'coop_probe_button'):
                    return
                self.coop_probe_button.configure(state='normal')
                if self.coop_vars['host_ip'].get().strip() != ip:
                    self.coop_probe_line.configure(
                        text=_('Server changed. Test again.',
                               'Адрес изменён. Проверьте снова.'), fg=CAUTION)
                    return
                self.coop_probe_line.configure(text=result, fg=color)
            self.ui_calls.put(display)
        try:
            threading.Thread(target=work, daemon=True).start()
        except RuntimeError:
            # Thread creation can fail during shutdown or resource exhaustion.
            self.coop_probe_pending = False
            self.coop_probe_button.configure(state='normal')
            self.coop_probe_line.configure(
                text=_('Unable to start TCP check. Please try again.',
                       'Не удалось запустить проверку TCP. Повторите попытку.'),
                fg=CAUTION)

"""
    src = exactly(src, "    def coop_changed(self):\n",
                  new_method + "    def coop_changed(self):\n",
                  "explicit per-click TCP probe method")
    return src
