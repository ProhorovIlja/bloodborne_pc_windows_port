# Bloodborne Seamless Hunt | Комплексная ревизия и консолидация
**Аудит:** 26.10.2026. **Каноническая WIP-ветка:** feature/shyt-win-fsr-countof-v63 (черновой PR #20). **Реальный статус:** до сих пор нет подтверждённого end-to-end запуска native EXE, полной Windows ZIP или Direct P2P gameplay.

## 1. Проверенный охват и доказательства
Обследованы полные деревья исходников (GitHub recursive Git trees, truncated=false), часть критических файлов, исходные контракты, API-дифф, публичные PR и реальные журналы CI:
- ProhorovIlja/bloodborne_pc_windows_port: **1 642 файла**, из них **27** workflow; в репозитории лежит исторический Windows GPU/runtime, но наш продукт теперь собирается из *отдельного* pinned Yharnam Together + наложений.
- lKaniel/bloodborne-server@0645740a33ae21c56df3b4a0d9777086dbca6053: **2 857 файлов** (исходники игрового клиента, Qt сервера, laucher, backend и тесты).
- CLSAMG22/BBSC@4f11faf88b6ba658ebde6fe5fbefdadedba4fa41: **1 419 файлов**.
- Amanises-Yharnam-Together/bloodborne-server@208c4f70718d1e73ef7deec2b4d3fdcc16ecce9a: **2 759 файлов**.
- Дифф **нашего pinned upstream** 77e350743a7cb4524cfcc1782fb6e3af64e25b15 и актуального YT 0645740a...: **180 commits, 300 changed paths**, среди них bbport 144, emulator 74, server 22. Ссылка: https://github.com/lKaniel/bloodborne-server/compare/77e350743a7cb4524cfcc1782fb6e3af64e25b15...0645740a33ae21c56df3b4a0d9777086dbca6053
Это **проверка состава**, а не построчный аудит каждого из многих тысяч файлов и тем более не гарантия отсутствия runtime-багов.

## 2. Системные причины и исправления
| Приоритет | Область | Наблюдение в реальных источниках | Критерий устранения |
| --- | --- | --- | --- |
| P0 | Native клиент | Полные Windows Clang64 jobs 40302711995 и 40303648350 вышли по таймауту 165 минут. У первой Ninja остановился на [119/418]; во второй не сохранился Ninja log. Обычный source CI PASS не доказывает сборку игры. | Настоящие Clang64 bbnet, рендерер, bb-play.exe, ZIP и 2-PC тест. V109–V116 улучшают source-gates, диагностику и ограничение параллельной сборки, но ещё не закрыли эту строку. |
| P0 | CI избыточность | V63 full и V103 real-bbnet компилировали тот же исходник в разных 180-мин Windows jobs на каждый push/PR; наблюдали девять одновременно работающих старых компиляторов. 27 workflow не являются единым pipeline. | **Атомарный batch V117:** full Windows компилирует настоящий bbnet → немедленно проверяет V108 (4 C++-объекта и 7 SHA256) → только после PASS компилирует GPU → ZIP. V103 source Windows/Ubuntu остается автоматическим; отдельный 180-мин bbnet-only запускается исключительно workflow_dispatch. |
| P0 | Устаревающая база | unified-v9/compose_sources.py, mainline/check_source_of_truth.py, source manifests и V97–V116 build patches содержат строгий SHA 77e3507 и исходные строковые якоря. Более новый upstream уже менял 300 файлов. | **Отдельный атомарный rebase** к новому проверенному upstream release tag, с тестовой матрицей пересечений, а не массовая замена PIN без пересборки и прогона контрактов. |
| P0 | Network/auth | p2p_route_policy.hpp и нативный adapter не подключены к проверенному серверному peer consent, identity/key lease, разрешениям по игровым каналам и реальной NAT доставке. Compose manifest явно указывает direct_udp NOT ENABLED. | Direct OFF до end-to-end authenticated UDP, anti-replay/ordering, NAT/proxy/CGNAT и надежного server relay fallback. Сервер сохраняет world authority и RPC. |
| P0 | Доверие серверу | В старом pinned сервере строгая binding member identity opt-in ради легаси клиентов. Клиентские PvP/gameplay читы и ходовые metadata нельзя считать авторитетными. Скриншоты будущей авторизации Yharnam Unbound показывают UX, а не защищенность DB. | Отдельный staging Qt shadnet с логином/банами/сменой пароля, пределами памяти, replay tests, malformed packets, version/guest compatibility и rollback; не трогать production Fornex. |
| P1 | Смерть/возрождение | В наших overlays V5/V97–V99 есть пересечения с YT merged #426 IsNoDead, #397 spectator/freecam и BBSC open #38 revive / #9 wipe / #22 respawn. | Один игровой state machine; два реальных игрока, смерть рядом с противником, giving up, ручное возрождение, boss wipe/fog, cross-area, spectator privacy, host leave. |
| P1 | FPS/launcher/UI | Новый YT изменил разрешения, ин-гейм меню, карту, команды, save/mode settings, kit, Qt и GPU. Наши V95 BL/build Discord preview и Quit Desktop источник-уровня, не тестировались в игре. | Новый baseline YT + сохранить лишь отсутствующие улучшения; auto game detection, region/version, safe saves/mod backups, opt-in Discord privacy, Quit, BL/build, camera, controller, recovery. |
| P1 | Производительность | Нет достоверной телеметрии 200 пользователей на совмещенных latest client/server. CPU, RSS, packets/second, forward bytes, crashes и DLSS/FSR длительного сеанса пока не измерены. | Профилировать staging, latency p50/p95, throughput, RAM, 2-hour soak, real sessions; не заявлять Direct выигрыша без измерений. |
| P1 | Честные релизы | Работающие PS4/BBport/legacy CLS клиенты не автоматически совместимы с новыми protocol 8/9/Noise. WIP анонс объединения BBSC × YT не равен выпущенному Yharnam Unbound. | Отдельная совместимая схема, handshake/version checks, тест плохого пароля и разрешений, отсутствие бесшумной миграции, подписанный updater, лицензии и credits. |

## 3. Заимствования: что уже есть, а что открытo
Yharnam Together: https://github.com/lKaniel/bloodborne-server
- В текущей mainline слиты (на проверенной ревизии) #426 hook dying corpse, #397 death spectate/free camera, #422 resolution, #419 launcher guide, #420 duel flows. Не накладывать поверх этих реализаций старые аналогичные патчи без сопоставления игровой семантики.
- Открытые PR: #423 друзья/open teams и identity, #403 host handover, #375 Noise NK encrypted **server link** (не Direct P2P), #368 link HMAC, #380 shard directory. Они еще не являются подтвержденной готовой функцией нашего клиента.
- Server/coop: есть CoopStream, GameLinkPeer, LinkAuth, Admission, tests/fuzz. Каждый предел и fallback проверять по **месту создания объекта** и фактическим C++ settings, а не только наличию константы в header.

BBSC: https://github.com/CLSAMG22/BBSC
- Public release v0.0.2. Открытые #38 revive, #39 blackout join, #42 Ludwig wall, #22 guest spawn, #9 boss wipe, #26 Communion Chalice, #14 reward/status effects.
- Это разные игровые runtime и реализации. Можно заимствовать корректные поведенческие тесты, но не автоматически смешать shadPS4/BBSC бинарный слой с native Windows.
- Acknowledgment и лицензии для YT, CLS, Amanises, Supermedo и зависимостей обязательны.

## 4. Единый release-контракт
1. Прозрачный pinned source-of-truth, фиксированный список overlays, SHA и полный пересмотр конфликтующих upstream исправлений.
2. Проверки source/CI с fuzz/UBSan, Python offline policy, C++ unit, Qt/Linux server staging и проверкой protocol version.
3. **Один** Windows CI native game job: CMake/ccache → bbnet actual C++ → V108 archive members+source digests → GPU → EXEs → ZIP+SHA+provenance. При любом сбое собирать CMake/Ninja error artifact, не публиковать неподтвержденную игру.
4. Два ПК/два игрока: host/join, random/private wrong-password, controller/keyboard, all death/revival paths, real host migration, boss/door/NPC, mod/regional saves, 2h soak, crashes, BL/Discord privacy, quit.
5. Server performance/availability: staging 200+ synthetic links, handshake flood/backpressure, relay bytes and CPU, NAT matrix, secure Direct fallback; никак не затронуть живой Fornex.
6. Публичный релиз с rollback, license/credits, без retail assets, без автоапдейта сохраняющихся персонажей/учёток без согласия.

## 5. Фиксация сделанного
В этом атомарном пакете **нет** перехода к новому upstream, нечестного включения Direct, замены старых сохранений или production deployment. Внедряется обязательная интегрированная проверка **реального** bbnet в полном Windows game job и устраняется второй тяжелый автоматический bbnet-only job. V103 source-matrix остается регулярной. Реальные результаты V117 CI, игра, сервер и runtime проверки еще необходимо получить.

Полная ревизия всех файлов построчно и обещание «всё исправлено» без работающего продукта были бы ложными. Этот документ сохраняет инвентаризацию, подтвержденные риски, последовательность и критерии, по которым действительно можно закрывать подсистемы.


## V123: native bbnet prerequisite runs Git/jj before any C++ object
Actual V120 Windows run 40350762787: CMake configured successfully (2.7s), then **bbnet-build.log was zero bytes** for 1830 seconds before V110 guard abort. GitHub cleanup orphaned ninja, cmd, cmake AND multiple git processes. Pinned original CMake has `add_dependencies(bbnet bbcoop_revision)`, and always-on `bbcoop_revision` runs `cmake -P bbcoop/revision.cmake`. Its original Git blob is 9b8aec040f81ef1a65f838065ad46de87046f040; it searches WinGet jj and then calls `git rev-parse HEAD` and `git status --porcelain`. This is a likely (not yet definitively proved) early Ninja blocker.
For immutable overlaid CI ONLY, V123 preserves the original revision string **77e350743a7cb4524cfcc1782fb6e3af64e25b15-dirty** and bypasses jj/Git probes in this CMake custom target using a checked environment variable. The source-exact patch only accepts the original Git blob; outside CI, original jj/git behavior remains unchanged. Real CMake script smoke checks exact #define output, no rewrite when unchanged, invalid pinned SHA fails closed. The subsequent full Windows build must show game C++ compilation, real bbnet archive provenance and playable GPU executable before the fix is considered closed.
