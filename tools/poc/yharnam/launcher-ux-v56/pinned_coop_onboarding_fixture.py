# SPDX-License-Identifier: GPL-2.0-or-later
# Extracted test-only methods from pinned lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15
# Original code copyright and attribution retained under upstream GPL-2.0-or-later.
def pinned_constructor(root):
    root.title(COOP_NAME if COOP_INSTALL else 'Bloodborne — bbport')

class PinnedCoopLauncherSubset:
    def build_coop_popup(self):
        """The co-op settings, over the whole window (Kaniel 2026-10-16): opened from the menu, and by
        itself at the first start; the launcher stays behind it until the game folder and the host's IP
        are set and Done is pressed."""
        tk, ttk, px = self.tk, self.ttk, self.px
        self.coop = bbport_coop.load_settings(PORT_DIR)
        self.coop_busy = self.coop_searching = False
        self.coop_required = False
        cover = self.coop_cover = tk.Frame(self.root, bg=BG)
        self.chrome.bind_drag(cover)
        strip = tk.Frame(cover, bg=BG)
        strip.place(relx=1.0, y=0, anchor='ne')
        for kind, command in (('close', self.close), ('min', self.chrome.minimize)):
            CaptionButton(self, strip, kind, command, bg=BG).pack(side='right')
        holder = tk.Frame(cover, bg=BG)
        holder.place(relx=0.5, rely=0.5, anchor='center', width=px(820))
        self.coop_help_holder = holder
        card = self.card(holder, _('Co-op', 'Кооператив'), pad=32)
        card.frame.pack_configure(padx=0, pady=0)
        card.columnconfigure(0, weight=1, uniform='coop', minsize=0)
        card.columnconfigure(1, weight=1, uniform='coop', minsize=0)
        self.coop_vars, self.coop_picked = {}, set()

        def var(key, value=None):
            v = tk.StringVar(value=self.coop.get(key, '') if value is None else value)
            v.trace_add('write', lambda *_a: self.coop_changed_soon())
            self.coop_vars[key] = v
            return v

        self.flow(card, _('Set co-op up once: where your game is, who hosts, and how hard the enemies are. '
                          'Everyone uses this same release; the others see your character\'s name.',
                          'Настройте кооператив один раз: где игра, кто хост и насколько сильны враги. '
                          'Все используют один релиз; другие видят имя вашего персонажа.'), 'body', MUTED).grid(
            row=1, column=0, columnspan=2, sticky='we', pady=(px(6), px(4)))
        cell = self.cell(card, 2, 0, _('Your Bloodborne folder (version 1.09, or with the 1.09 update next to it)',
                                       'Папка Bloodborne (версия 1.09 или с обновлением 1.09 рядом)'), span=2)
        holder = tk.Frame(cell, bg=CARD)
        holder.pack(fill='x')
        ttk.Entry(holder, textvariable=var('game'), width=30).pack(side='left', fill='x', expand=True)
        self.button(holder, _('Browse…', 'Обзор…'), self.coop_browse).pack(side='left', padx=(px(8), 0))
        self.button(holder, _('Find it for me', 'Найти автоматически'),
                    lambda: self.coop_search(None)).pack(side='left', padx=(px(8), 0))
        self.pkg_button(holder).pack(side='left', padx=(px(8), 0))
        self.coop_game_line = StatusLine(self, cell)
        self.coop_game_line.frame.pack(fill='x', pady=(px(6), 0))

        def combo(cell, key, options):
            values = [v for v, _t in options]
            box = ttk.Combobox(cell, values=[_(*t) for _v, t in options], state='readonly', width=30)
            box.current(values.index(self.coop.get(key)) if self.coop.get(key) in values else 0)
            v = var(key, values[box.current()])

            def picked(_e):
                self.coop_picked.add(key)
                v.set(values[box.current()])
                self.coop_changed_soon()
            box.bind('<<ComboboxSelected>>', picked)
            box.pack(fill='x')
            if self.coop.get('confirmed') != '1':
                box.set('')  # chosen once by the player (Kaniel 2026-10-16), not taken by default
            else:
                self.coop_picked.add(key)
            return box

        # No Player/Host switch (Kaniel 2026-10-16): the host types their own address and starts the server
        # with Start server (Kaniel 2026-10-21: PLAY no longer starts it).
        cell = self.cell(card, 3, 0, _("Host's IP address (VPN or public; the host types their own)",
                                       'IP хоста (VPN или внешний; хост вводит свой)'))
        ttk.Entry(cell, textvariable=var('host_ip')).pack(fill='x')
        # No account name or password (phase 11): the player's id is made once and kept in coop.json,
        # and the others see the character's name. No party settings: the team is made in the game (the team screen after Continue).
        enemies = self.cell(card, 3, 1, _('Enemies (the same for every player)', 'Враги (у всех одинаково)'))
        saved = self.coop.get('harder', 'off')
        presets = [v for v, _t in HARDER_CHOICES if v != 'custom']
        custom = saved not in presets and bbport_coop.valid_harder(saved)
        if custom:
            self.coop['harder'] = 'custom'  # the box shows Custom; the variable gets the rates back below
        self.coop_enemies = combo(enemies, 'harder', HARDER_CHOICES)
        self.build_coop_custom(enemies, saved if custom else bbport_coop.HARDER_ON)
        if custom:
            self.coop['harder'] = saved
            self.coop_custom_changed()

        def enemies_picked(_e):
            if self.coop_enemies_choice() == 'custom':
                self.coop_custom.pack(fill='x', pady=(px(8), 0))
                self.coop_custom_changed()
            else:
                self.coop_custom.pack_forget()
        self.coop_enemies.bind('<<ComboboxSelected>>', enemies_picked, add='+')
        holder = self.cell(card, 4, 0, '', span=2)
        # Players were lost at the VPN step (Kaniel 2026-10-21): the steps are one press away. Below the
        # fields, so Host IP and Enemies stay on one line.
        self.button(holder, _('How to connect', 'Как подключиться'), self.open_coop_help).pack(side='left')
        self.button(holder, _('Bring saves from another folder…', 'Перенести сохранения из папки…'),
                    self.coop_import_saves).pack(side='left', padx=(px(8), 0))
        self.note(card, _('Make or join a team in the game: Continue, Load Game or New Game opens the team screen. '
                          'Windows asks once to let co-op through its firewall.',
                          'Команду собирают в игре: «Продолжить», «Загрузить» или «Новая игра» открывают экран '
                          'команды. Windows один раз спросит разрешение для брандмауэра.'), top=16)
        done_row = tk.Frame(card, bg=CARD)
        done_row.grid(row=self.next_row(card), column=0, columnspan=2, sticky='we', pady=(px(22), 0))
        self.coop_done = self.button(done_row, _('Done', 'Готово'), self.close_coop, 'primary', width=px(150))
        self.coop_done.pack(side='right')
        self.coop_missing = self.label(done_row, '', 'small', CAUTION)
        self.coop_missing.pack(side='right', padx=(0, px(16)))
        self.coop_host = done_row  # coop_changed waits for the card to be built
        self.coop_card = card.frame
        self.coop_help = None
        self.coop_changed()
        if not self.coop_game_folder():
            self.coop_search(None, quiet=True)


    def coop_changed(self):
        self.coop_change_job = None
        if not hasattr(self, 'coop_done'):
            return
        for key, v in self.coop_vars.items():
            self.coop[key] = v.get().strip()
        try:
            bbport_coop.save_settings(PORT_DIR, self.coop)
        except OSError:
            pass
        self.coop['role'] = 'host' if bbport_coop.is_this_pc(self.coop.get('host_ip', '')) else 'guest'
        if not self.coop_searching:
            self.coop_show_game()
        missing = self.coop_ready()
        self.coop_done.configure(state='disabled' if missing else 'normal')
        self.coop_missing.configure(text=_('Still needed: {}', 'Ещё нужно: {}').format(', '.join(missing))
                                    if missing else '')
        if hasattr(self, 'checks'):
            self.refresh_status()
            self.refresh_game_line()

