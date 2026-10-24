#!/usr/bin/env python3
"""V56 original BLauncher Tkinter first-run co-op polish.

Only the pinned Yharnam Together launcher is transformed. This deliberately
does NOT invent a new login system, save passwords outside coop.json, point to
an untested production port, change game config, or add external client modes.
"""
from __future__ import annotations

def once(source: str, old: str, new: str, label: str) -> str:
    found = source.count(old)
    if found != 1:
        raise ValueError(f"V56 pinned Tkinter launcher drift ({label}): {found}")
    return source.replace(old, new, 1)


def transform(source: str) -> str:
    if "SHYT_LAUNCHER_ONBOARDING_V56" in source:
        raise ValueError("V56 launcher onboarding already installed")
    source = once(source,
        "root.title(COOP_NAME if COOP_INSTALL else 'Bloodborne — bbport')",
        "root.title(('Seamless Hunt  |  ' + COOP_NAME) if COOP_INSTALL else 'Bloodborne — bbport')",
        "original Yharnam launcher window title")
    source = once(source,
        "card = self.card(holder, _('Co-op', 'Кооператив'), pad=32)",
        "card = self.card(holder, _('Yharnam Together  ·  Co-op', 'Yharnam Together  ·  Кооператив'), pad=32)",
        "co-op onboarding card branding")
    source = once(source,
        "        self.coop_vars, self.coop_picked = {}, set()\n",
        """        self.coop_vars, self.coop_picked = {}, set()
        # SHYT_LAUNCHER_ONBOARDING_V56: quiet, accessible readiness indicator.
        # Never echo the account secret, tokens or even the account name here.
        hero = tk.Frame(card, bg=CARD)
        hero.grid(row=1, column=0, columnspan=2, sticky='we', pady=(px(6), px(1)))
        hero.columnconfigure(0, weight=1)
        self.label(hero, _('SEAMLESS HUNT', 'SEAMLESS HUNT'), 'h1', GOLD,
                   bg=CARD).grid(row=0, column=0, sticky='w')
        self.coop_setup_progress = self.label(hero, '', 'small_bold', MUTED,
                                              bg=CARD)
        self.coop_setup_progress.grid(row=0, column=1, sticky='e', padx=(px(10), 0))
        self.label(hero, _('Yharnam Together client · One connected world',
                           'Клиент Yharnam Together · Один общий мир'),
                   'small', MUTED, bg=CARD).grid(row=1, column=0,
                                                columnspan=2, sticky='w',
                                                pady=(px(2), px(4)))
""",
        "insert one shared-world first-run hero")
    # The original prose contains an escaped apostrophe that varies in
    # serialized Python text. Match the pinned method boundaries, not a
    # typographic quote, while still refusing missing/drifted anchors.
    intro_start = source.find("        self.flow(card, _('Set co-op up once:")
    intro_end = source.find("        cell = self.cell(card, 2, 0,", intro_start)
    if intro_start < 0 or intro_end < intro_start:
        raise ValueError("V56 original co-op introductory text anchor drift")
    intro = """        self.flow(card, _('Find Bloodborne, choose your Yharnam Together server and confirm the '
                          'shared enemy difficulty. No other multiplayer client is required.',
                          'Найдите Bloodborne, выберите сервер Yharnam Together и подтвердите '
                          'общую сложность врагов. Другие клиенты мультиплеера не нужны.'),
                  'body', MUTED).grid(
            row=2, column=0, columnspan=2, sticky='we', pady=(px(6), px(4)))
"""
    source = source[:intro_start] + intro + source[intro_end:]
    source = once(source,
        """        cell = self.cell(card, 2, 0, _('Your Bloodborne folder (version 1.09, or with the 1.09 update next to it)',
                                       'Папка Bloodborne (версия 1.09 или с обновлением 1.09 рядом)'), span=2)
""",
        """        cell = self.cell(card, 3, 0, _('01  ·  Bloodborne game folder (1.09 or external 1.09 patch)',
                                       '01  ·  Папка Bloodborne (1.09 или обновление 1.09 рядом)'), span=2)
""",
        "game finder field with numbered sequence")
    source = once(source,
        """            if self.coop.get('confirmed') != '1':
                box.set('')  # chosen once by the player (Kaniel 2026-10-16), not taken by default
            else:
                self.coop_picked.add(key)
""",
        """            if self.coop.get('confirmed') != '1' and key != 'harder':
                box.set('')
            else:
                # Keep the safe vanilla enemy preset 'off' on first run.
                # An explicit difficulty change is still available.
                self.coop_picked.add(key)
""",
        "safe first-run vanilla enemy preset")
    source = once(source,
        """        cell = self.cell(card, 3, 0, _("Host's IP address (VPN or public; the host types their own)",
                                       'IP хоста (VPN или внешний; хост вводит свой)'))
""",
        """        cell = self.cell(card, 4, 0, _('02  ·  Yharnam Together server IP (private or dedicated)',
                                       '02  ·  IP сервера Yharnam Together (частный или выделенный)'))
""",
        "server address role")
    source = once(source,
        """        enemies = self.cell(card, 3, 1, _('Enemies (the same for every player)', 'Враги (у всех одинаково)'))
""",
        """        enemies = self.cell(card, 4, 1, _('03  ·  Shared enemy difficulty',
                                           '03  ·  Общая сложность врагов'))
""",
        "shared enemies section")
    source = once(source,
        "        holder = self.cell(card, 4, 0, '', span=2)\n",
        "        holder = self.cell(card, 5, 0, '', span=2)\n",
        "actions below all three fields")
    source = once(source,
        "self.button(holder, _('How to connect', 'Как подключиться'), self.open_coop_help)",
        "self.button(holder, _('Connection help', 'Помощь с подключением'), self.open_coop_help)",
        "network help button")
    source = once(source,
        """        self.note(card, _('Make or join a team in the game: Continue, Load Game or New Game opens the team screen. '
                          'Windows asks once to let co-op through its firewall.',
                          'Команду собирают в игре: «Продолжить», «Загрузить» или «Новая игра» открывают экран '
                          'команды. Windows один раз спросит разрешение для брандмауэра.'), top=16)
""",
        """        self.note(card, _('Create or join co-op teams inside the Yharnam Together game. '
                          'Your local account identity stays in this installation. '
                          'Continue, Load Game or New Game opens the team screen.',
                          'Создавайте команды и вступайте в них внутри Yharnam Together. '
                          'Локальная учётная запись остаётся в этой установке. '
                          '«Продолжить», «Загрузить» и «Новая игра» открывают экран команды.'), top=16)
""",
        "privacy note and one-client in-game team")
    source = once(source,
        "self.button(done_row, _('Done', 'Готово'), self.close_coop, 'primary', width=px(150))",
        "self.button(done_row, _('CONTINUE', 'ПРОДОЛЖИТЬ'), self.close_coop, 'primary', width=px(160))",
        "clear call-to-action")
    source = once(source,
        """        missing = self.coop_ready()
        self.coop_done.configure(state='disabled' if missing else 'normal')
""",
        """        missing = self.coop_ready()
        # The readiness indicator tracks real game/server/enemy checks only.
        # Do not show secrets or claim that a remote server is reachable.
        count = 3 - len(missing)
        self.coop_setup_progress.configure(
            text=_('{}/3 ready', '{}/3 готово').format(count),
            fg=OK if not missing else (CAUTION if count else MUTED))
        self.coop_done.configure(state='disabled' if missing else 'normal')
""",
        "live setup progress without network false positives")
    return source
