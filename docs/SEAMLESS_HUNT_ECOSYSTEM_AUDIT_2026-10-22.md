# Seamless Hunt PC — аудит экосистемы Bloodborne (22.10.2026)

**Задача:** один нативный Windows-клиент, один лаунчер, одна учётная запись Seamless Hunt, надёжный seamless co-op, direct P2P с fallback, моды, настройка под железо. НЕ распространять/сопровождать отдельные сторонние клиенты. Существующий публичный BBSC/VPS не заменять без испытаний.

Это обзор *проверенных 22 октября 2026* публичных деревьев/документации, а не обещание, что каждый коммит каждого форка уже прошёл ручной аудит. Все «можно взять» ниже — кандидаты до компиляции, измерений и лицензирования. Некоторые проекты включают чужой код: сначала проверять происхождение изменений, а не копировать дубликаты.

## 1. Решение по основе

**Основной код:** `ProhorovIlja/bloodborne_pc_windows_port`, ветка `feature/seamless-hunt` (visy 0.7.2 lineage). Это уже нативное выполнение игрового x86-64 кода, Win32 runtime, Vulkan renderer/shader translation, seamless co-op, прямой TCP/UDP, NAT/STUN, DHT option, member relay, BBP3-коды, сохранения, моды, FPS/FSR/DLSS/HDR и тесты.

«Нативный» здесь НЕ значит полностью переписанный движок игры и НЕ значит отсутствие графической трансляции: используется часть кодовой базы shadPS4 для GPU. Отдельный эмулятор shadPS4 для запуска не нужен. Игра по-прежнему требует собственный легальный дамп версии 1.09.

**Важная оговорка качества:** `docs/party/ERSC_PARITY.md` на 22 октября сам оценивает подтверждённое соответствие seamless примерно в 89%; для исправлений 0.7.2 подтверждения реальным двух-PC интернет-сеансом недостаточно. Не превращать «тесты прошли» в «онлайн идеален».

## 2. Изученные upstream / форки и уникальная полезность

### Нативное ядро, рендеринг, производительность
1. **visy/bloodborne_pc_windows_port** — основа. `gpu/shim/party/`, `gpu/shim/`, `src/`, `scripts/mods.py`, `launcher.py`, `tests/`. Сохранять более свежие кооперативные изменения; не перезаписывать версиями от производных форков. https://github.com/visy/bloodborne_pc_windows_port
2. **deadinside28/bloodborne_pc** — корневой нативный Linux bbport, model of CPU/graphics runtime, новый memory/translation model, GPU queues, shader/motion vectors, frame hooks. `src/`, `gpu/`, `scripts/`. Особенно изучать архитектуру и изменения memory model отдельно под GPU. https://github.com/deadinside28/bloodborne_pc
3. **Mrsuss60/bloodborne_pc_windows_port** — базовая Win32 адаптация, TLS, Vulkan/SDL3, input, save/audio, small CPU compatibility, stability. Большинство этих вещей уже наследуются visy. https://github.com/Mrsuss60/bloodborne_pc_windows_port
4. **Supermedo/bloodborne_pc** — Windows online shadNet bridge (`gpu/bbnet/`), зрелый Python launcher (`launcher/`), автонастройка hardware и *isolated repeatable game benchmarks* (`launcher/bbport_benchmark.py`), 13 языков, frame generation, crash diagnostics, update UX. Сначала сравнить с visy по исходным SHA; особенно перенять методику бенчмарка, НЕ заменять co-op visy. https://github.com/Supermedo/bloodborne_pc
5. **Awakenchan/LanternEngine** — опубликованный `engine/bbhost-changes.patch` **поверх конкретного DarkIzuku baseline**; не полноценная самостоятельная история всех выпускаемых двоичных версий. Потенциальны рендер-производительность, VRAM budget/cleanup, GPU submission, frame pacing, shader pipeline, occlusion, crash fixes, input. `engine/README.md`, `engine/online/`, `launcher/windows/`. Сверять настройки, переписанные хуки, GPU/driver-specific ограничения. https://github.com/Awakenchan/LanternEngine
6. **DarkIzuku/bloodborne_pc** — Windows starting point Lantern, WPF, рендер и графические настройки; полезно для воспроизведения patch chain, а не как второй клиент. https://github.com/DarkIzuku/bloodborne_pc
7. **IFreemz/shadPS4-Bloodborne-DLSS-FSR** — у Awaken/прочих указано происхождение VRAM pacing / upscale fixes; исходный репозиторий/коммиты нужно проверять отдельно. https://github.com/IFreemz/shadPS4-Bloodborne-DLSS-FSR
8. **AwesomeObserver/bloodborne_pc** — стабилизация Windows, controller/raw input, графические опции, экспериментальные RTX пути. Сложный ray tracing эксперимент НЕ добавлять «по умолчанию». https://github.com/AwesomeObserver/bloodborne_pc
9. **0xCydral/bloodborne_pc** — PKG import, XeSS/FSR4/FG, простой установщик и GPU capability UI; изучать `launcher/`, `packaging/` и проверки аппаратных возможностей. https://github.com/0xCydral/bloodborne_pc
10. **FIocker/bloodborne_pc** — lineage оптимизаций FG/Reflex, уже частично в visy/Supermedo; только конкретные отсутствующие исправления. https://github.com/FIocker/bloodborne_pc
11. **FireBurn/FSR-Vulkan**, **dvj5411/fsr4vk** — низкоуровневые Vulkan FSR contracts/providers, имеют отличия между аналитическим FG, FSR4 и ML FG. Не маркировать одно другим; поддержка зависит от GPU/драйвера. https://github.com/FireBurn/FSR-Vulkan , https://github.com/dvj5411/fsr4vk

### Co-op / игровой процесс / сетевой код
12. **vladtepes22/NightwatchCoop** — *доказанная интеграция в исходниках* Awaken Lantern 0.9.36 + visy seamless 0.7.1. Ценен шаблон для hooking/engine integration и WPF launcher; **НЕ отдельный новый транспорт**. `engine/gpu/shim/party/`, `INTEGRATION.md`, `launcher/windows/`, `tools/smoke-coop.py`. SHA `party_netpath.cpp`, `party_rdv.cpp`, `party_crypto.cpp` у Nightwatch идентичны текущему visy; `party_death_rules.h` отличается (visy более новая 0.7.2). https://github.com/vladtepes22/NightwatchCoop
13. **Artificial-Sweetener/BloodBorneButPc** — ранняя интеграция движка Awaken/visy, упомянута Nightwatch; полезна история причин конфликта игровых хуков. https://github.com/Artificial-Sweetener/BloodBorneButPc
14. **lKaniel/bloodborne-server (Yharnam Together)** — отдельная архитектура: общий мир с центральным сервером, `server/coop/{team_lobby,world_log,packet_routes,coop.proto}`, downed/revive ударами, общие объекты, лобби, проверка последовательности и восстановление состояния. **Не копировать** централизованный транспорт в visy P2P. Заимствовать только адаптируемые правила и идеи тестов. `docs/BBPORT.md` явно утверждает: bbport и shadPS4 пользователи не находятся в одной партии на той реализации. https://github.com/lKaniel/bloodborne-server
15. **droogie/bbhost** — более нативное построение GPU draws из объектов игры, частная сеть NP/Matching2, HTTPS аккаунты, серверный STUN+relay, расширенный SDK API хуков, **TOML overrides параметров**, патч-манифесты с проверкой исходных байт и `eboot` hash, DLL/SO plugins (randomizer, boss rush, mutators), модо-разделение сессий. Сильный источник для *будущей* mod/plugin framework и PC-style renderer. Код плагинов тесно связан с runtime bbhost, поэтому нельзя загружать их DLL в visy напрямую. `docs/{modding,plugins,online}.md`, `include/bbhost_plugin.h`, `src/net/`. https://github.com/droogie/bbhost
16. **CLSAMG22/BBSC** — наш legacy shadPS4 client, 5-player experiments, bells, persistent area/boss sessions, patched client, Qt launcher/accounts; сохранение истории игры/логики совместимости. Отдельные hooks эмулятора не вставлять напрямую в нативный runtime. `emulator/src/core/bloodborne_re.cpp`, `server/gameserver/`, `bbport/bbport-1.7.2-bbsc.patch`. https://github.com/CLSAMG22/BBSC
17. **shadps4-emu/shadPS4** — upstream GPU shader correctness, файл/пакет модов, NP/HTTP compatibility, работающая база эмуляторных HLE. Для native клиента пересматривать только конкретные изменения общего графического кода и сетевых библиотек. Никакого второго shadPS4 в пользовательской установке. https://github.com/shadps4-emu/shadPS4
18. **Wozzardman/shadp2p** — ветка эмулятора с P2P, игровые network hooks и исследования summons; совместимость с legacy. https://github.com/Wozzardman/shadp2p
19. **Wozzardman/shadnet-p2p** — server matchmaking, summon broker, signaling, accounts, STUN и WebAPI. Особенность: описанный TCP игровой протокол 31313 сам по себе **не шифруется**. Не передавать пароли пользователей или чувствительные токены по открытому соединению без защищённого gateway. https://github.com/Wozzardman/shadnet-p2p
20. **shadps4-emu/shadNet** — общий upstream сервера: протокол, профили/матчмейкинг, конфиги; сравнивать отдельно с Wozzardman и нашим production server. https://github.com/shadps4-emu/shadNet

### Launcher, splitscreen, утилиты
21. **Nightwatch WPF Launcher** — `launcher/windows/BloodborneLauncher/Core/{Updater,SeamlessSession,SeamlessSettings,PlayerProfiles,GameRunner}.cs`; страницы `Views/`. Сохраняет `user`, `mods`, конфиги; авторизация у Nightwatch не заменяет Seamless Hunt. Проверенная beta 10.1 исправляет блокировки DLL при обновлении. **Недостаточно** для наших релизов: не обнаружена проверка SHA-256/подписи скачиваемого zip, копирование файлов не полностью атомарно. Требуется свой signed manifest + staged install + rollback.
22. **framilano/BloodborneNucleusCoopHandler** — подтверждённая документация по локальному мультиинстансу bbhost/bbport/BBSC, в том числе наш `play.seamlesshunt.com`; полезно поддержать опциональный split screen, а не устанавливать по умолчанию. https://github.com/framilano/BloodborneNucleusCoopHandler
23. **pyL1nx/bloodborne_pc** — achievement/trophy tracking и лаунчер, сравнить с тем, что уже есть у visy, bbhost и Supermedo. https://github.com/pyL1nx/bloodborne_pc
24. **fhody125-web/NoDreamForHunter** — локальный backend для сервисных API Bloodborne; нужен для офлайна/тестирования сервера, но не новая обязательная подсистема. https://github.com/fhody125-web/NoDreamForHunter

## 3. Функциональная матрица решений (не слепое копирование)

| Подсистема | База | Что изучить/добавить | Обязательная проверка |
|---|---|---|---|
| Нативный runtime | visy + lineage deadinside/Mrsuss60 | Awaken memory/draw, bbhost native draw path | CPU/GPU/driver compatibility, real game boot, exceptions |
| Графика и FPS | visy: FSR/DLSS/HDR/FG | Awaken frame pacing/VRAM/occlusion, Supermedo FG/ML, Cydral XeSS | A/B: одинаковая сцена/моды/шейдерный кеш, p50/p95/p99 frametimes, 1% lows, VRAM, artifacts |
| Онлайн игра | visy 0.7.2 party + encrypted direct P2P | route selection, retries, IPv6, NAT, **optional** authenticated VPS relay | реальная пара ПК, NAT/CGNAT матрица, disconnect/rejoin, wrong password always rejected |
| Account + discovery | Seamless Hunt existing services | HTTPS device login/PKCE, lobby, invite code, friend presence | no secrets in logs, auth over TLS, session ACL, rate limiting, revoke |
| Legacy BBSC | действующий шадNet + GameServer + native relays | versioned capability discovery; optional protocol bridge | проверка *каждого* направления BBSC/shadPS4 ↔ native; общий shadNet ≠ совместимость |
| Death/respawn/boss/lamps | visy с сохранением | сравнение Yharnam Together rules, guest revive, heal via hit, one-world tradeoffs | соло + 2/3/4 игрока, wipe, сохранения, boss state, cutscene |
| Моды и патчи | visy loose overlays/XML | bbhost TOML param edits, hash+expected byte checks, optional plugins via **новый совместимый ABI** | 1.09/edition checks, no game dump modification, load order, safe sandbox/rollback |
| Лаунчер | текущий visy Python GUI | Nightwatch WPF оболочка, Supermedo presets/benchmark, Cydral installation UX | Windows packaging, settings parity, native logs, UX, no user data loss |
| Обновления | GitHub Releases staging | манифест с подписью/хешами, separate channels, rollback, delta later | interrupted transfer, running game, locked DLL, low disk, corrupt archive |
| Данные и профили | user/ + save backups | profiles, modpacks, shared campaign migration safeguards | backup, offline, corrupted saves, imported saves |
| Диагностика | visy + BBSC logs | Supermedo auto benchmark, privacy-safe support bundle, route/latency indicators | log redaction and replayable A/B metrics |

## 4. Предпочтительная архитектура Seamless Hunt PC

```
                        [Единый Windows launcher]
      game folder, GPU detection, accounts, mods, updates, diagnostics
                                  |
                         [Native Bloodborne]
              visy runtime + selected Awaken/bbhost fixes
                                  |
             [Seamless gameplay/session compatibility API]
                                  |
                   [Encrypted direct P2P preferred]
                 NAT/STUN/IPv6 + peer/member relay
                                  |
                    [Optional Seamless Hunt relay]
                only when direct route really fails
                                  ^
                                  |
        [Seamless Hunt HTTPS account + session discovery gateway]
          website registration / login / token / invites / ACL
                                  |
             [existing production shadNet + GameServer]
               preserve legacy BBSC traffic as it is
```

**Account:** регистрируется через сайт, лаунчер открывает браузер для авторизации; ограниченный токен возвращается клиенту безопасным потоком (например device code или OAuth2/PKCE при наличии собственной поддержки), хранится в Windows Credential Manager/DPAPI, можно выйти и отозвать устройство. Пароль не хранить в `launcher_settings.json`. Текущий game-protocol shadNet 31313 не использовать для передачи незащищённых учётных данных.

**Sessions:** discovery отвечает только за поиск/описание и аутентифицированное право на подключение; сам трафик игры идёт по visy P2P. Никогда не размещать полный BBP3 party secret в открытой выдаче. Серверный relay должен проверять ограниченный токен сессии и состояние подключения, применять E2E аутентификацию, лимиты трафика и SLA; существующий relay v15/v17 на VPS не является plug-and-play транспортом visy.

**Legacy:** старый BBSC использует другие игровые и сетевые сообщения; нужен отдельный протокол/синхронизация и тесты, если окажется возможным. Не обманывать игроков меткой «совместим» только за совпадение логина или адреса сервера.

## 5. Как выбирать «лучшее» без регрессий

1. **Inventory + de-dup:** для каждого кандидата фиксируем upstream commit, лицензии, файлы, уже наследуется? (пример: Nightwatch/visy три сетевых файла с идентичными Git blob SHA).
2. **Minimal patch:** отдельный обратимый коммит, feature flag по умолчанию off для рискованных GPU/gameplay функций.
3. **Baseline:** исходная visy на одинаковых игровых сценах/драйвере/разрешении/кеше; сравнить с собранным кандидатом, в том числе 4/6/8/12+ GB VRAM и NVIDIA/AMD/Intel, если есть реальные тестовые машины.
4. **Tests:** unit → Windows builds → engine smoke → 2 local instances → 2 real internet PCs → longer multi-hour party. **GitHub Actions Python success не равен полной Windows сборке.**
5. **Security:** не логировать токены, пароли, секреты; TLS и аутентификация на каждом маршруте; сохранить пользователей и production VPS.
6. **Release:** source commit + license notices + builds with verified archive, back up saves, staging rollout, rollback. Public GitHub repo must never contain retail game assets, users' data or credentials.

## 6. Рекомендуемый порядок работ (всё в ОДНОМ GitHub репозитории)

**P0: Базовая стабильность**
- зафиксировать baseline `feature/seamless-hunt`, подтянуть upstream visy в отдельном проверяемом merge, не потеряв наши commits;
- reproducible Windows build + test artifacts, 2-PC baseline before engine rewrites;
- smoke integration test, save protection, error log path.

**P1: Сетевой слой Seamless Hunt**
- настоящий contract сервера: безопасный login, session discovery/invite, versioned protocol capabilities;
- прямой P2P visy не меняется, при неуспехе optional relay; независимые аккаунты от игровых кодов;
- подробный NAT/password/CGNAT/reconnect testing, старые клиенты работают отдельно.

**P2: Лучше движок на реальном железе**
- сравнить Awaken changes patch + bbhost нативные GPU draws с visy по фактическим A/B, взять только выигрышные совместимые правки;
- Supermedo `bbport_benchmark.py` как источник для встроенного мастера «Best settings for my PC»;
- пресеты low VRAM/balanced/quality, без обещания работы на неподдерживаемых CPU/GPU.

**P3: Свой единый лаунчер**
- выбрать WPF (Nightwatch) после proof-of-concept и parity test, или оставить Python frontend, пока он надёжнее;
- управление аккаунтом на сайте, вход, друзья/онлайн, моды/патчи и профили, Discord/сайт, GPU recommendations, changelog;
- защищённый updater с rollback, сохранения не трогать, single launcher exe.

**P4: Игровые механики + моддинг**
- ролевые правила seamless, оптимизированные death/revive, shared world, разделение модифицированных и чистых групп;
- param patches и позже native plugins через версионированный ABI (не прямой импорт несовместимых DLL bbhost);
- расширения вроде split-screen Nucleus как opt-in, а не обязательная часть.

## 7. Что уже есть и что НЕ сделано

**Есть:** аккаунты/сеть работающего VPS, архивы Windows/Server, source bundles TCP relay v15 / UDP v17, visy fork и ветка `feature/seamless-hunt`, read-only diagnostic Seamless Hunt, автоматические Python regression tests, опубликованный пример Nightwatch bridge, текущие научно-технические ссылки.

**НЕ сделано:** native account sign-in, native session discovery, native↔legacy игровой protocol bridge, integration с VPS relay для visy transport, доказанный A/B performance winner, единый WPF launcher production, полноценная Windows CI/build artifact текущего Seamless Hunt fork, реальный 2-PC live pass на текущей ветке. Не приравнивать изучение репозитория к переносу функционала.

## 8. Исходные ограничения и честная оговорка

- Стандартные игровые файлы/eboot/проприетарные ассеты не публиковать.
- Совместимость лицензий GPL-2.0-only и GPL-3.0-only проверять по **файлам**; основа visy GPL-3.0-or-later, Awaken engine и bbhost GPL-3.0-or-later, многие исходные проекты GPL-2.0-or-later, отдельные MIT.
- «Любое железо» недостижимо: visy требует Windows x64, AVX2 и Vulkan 1.3; DLSS, FG и memory model зависят от производителя GPU. Цель — лучшие безопасные настройки **для поддерживаемого железа**, с честным указанием минимальных требований.
- Этот обзор исходников и архитектуры не является полной построчной экспертизой тысяч изменений. Для каждого переноса нужен прицельный просмотр diff и тесты.

## 9. Референсы / дальнейшее чтение
- visy [readme](https://github.com/visy/bloodborne_pc_windows_port), [party evidence](https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/party/ERSC_PARITY.md), [build](https://github.com/visy/bloodborne_pc_windows_port/blob/master/docs/BUILDING.md)
- Awaken [LanternEngine](https://github.com/Awakenchan/LanternEngine), [engine patch README](https://github.com/Awakenchan/LanternEngine/blob/main/engine/README.md)
- Nightwatch [integration](https://github.com/vladtepes22/NightwatchCoop/blob/main/INTEGRATION.md), [WPF updater](https://github.com/vladtepes22/NightwatchCoop/blob/main/launcher/windows/BloodborneLauncher/Core/Updater.cs)
- bbhost [mods](https://github.com/droogie/bbhost/blob/master/docs/modding.md), [plugins](https://github.com/droogie/bbhost/blob/master/docs/plugins.md), [online](https://github.com/droogie/bbhost/blob/master/docs/online.md)
- Yharnam Together [architecture](https://github.com/lKaniel/bloodborne-server/blob/main/docs/BBPORT.md), [lobby](https://github.com/lKaniel/bloodborne-server/tree/main/server/coop)
- Supermedo [benchmark](https://github.com/Supermedo/bloodborne_pc/blob/windows/launcher/bbport_benchmark.py), [native shadNet bridge](https://github.com/Supermedo/bloodborne_pc/blob/windows/gpu/bbnet/SHADNET-PORT.md)
- Wozzardman [shadnet-p2p](https://github.com/Wozzardman/shadnet-p2p), [shadp2p](https://github.com/Wozzardman/shadp2p)
- Current work: [source baseline](SEAMLESS_HUNT_STATUS.md), [connectivity](SEAMLESS_HUNT_CONNECTIVITY.md), [Nightwatch audit](NIGHTWATCH_COOP_EVALUATION.md).

**Правило:** одно пользовательское приложение и один user-owned repo; внешний проект = источник проверяемого изменения, а не дополнительный продукт, который пользователь должен поддерживать.

## 10. Фактическое сравнение Git tree (по blob SHA)

Исследование от 22 октября: получены полные рекурсивные Git tree для исходников visy, Nightwatch, Supermedo и deadinside28. Сравнение — по *совпадающим относительным путям* (`engine/` у Nightwatch отброшен), только `gpu/`, `src/`, `scripts/`, `launcher/`, `tests/`, `tools/`, с исключением большинства vendored / docs / third_party путей. Это **не** полноценный semantic diff, а карта объёма для дальнейшего review:

| Сопоставление к visy | Совпадающих путей | Побайтово одинаковых Git blobs | Отличающихся blobs | Только в сравниваемом дереве |
|---|---:|---:|---:|---:|
| Nightwatch (`engine/`) | 447 | 317 | 130 | 233 |
| Supermedo (`windows`) | 131 | 40 | 91 | 212 |
| deadinside28 | 181 | 74 | 107 | 624 |

**Следствие:** Nightwatch уже содержит много идентичного visy-кода, но его собственное окружение, `gpu/bbnet/`, WPF launcher и Awaken-правки требуют отдельного port/diff. Более 600 эксклюзивных файлов deadinside — не 600 доказанных улучшений: часть просто не совпадает структурой каталога и платформой. Сырые количества не являются метрикой качества. У LanternEngine публичный Git tree не содержит сборочного дерева полного движка, а содержит `engine/bbhost-changes.patch` к DarkIzuku, поэтому автоматическое сравнение по одинаковым путям не информативно.

Критически важные точки сравнения: `gpu/shim/bbgpu.cpp`, `gpu/shim/bbport_copy.cpp`, `gpu/shim/bbport_frame_state.h`, `gpu/shim/bbport_guest_hooks.cpp`, `gpu/shim/bbport_settings.cpp`, Network `gpu/bbnet`. Для патчей нужно сверить upstream commit и область владения frame hooks, а не только хеш.
