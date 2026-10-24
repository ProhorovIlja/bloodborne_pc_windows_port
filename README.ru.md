# Seamless Hunt: Bloodborne PC

[**English README and project description**](README.md) · [Credits and original developers](CREDITS.md) · [Licenses and third-party notices](THIRD_PARTY_NOTICES.md) · [Contribution policy](CONTRIBUTING.md)

**Seamless Hunt** это экспериментальная модификация [Yharnam Together](https://github.com/lKaniel/bloodborne-server): нативный порт Bloodborne на Windows, лаунчер **BLauncher от Yharnam Together**, кооператив и сервер shadNet с нашими изменениями. Это **не** старый Linux-порт из `master`, не лаунчер Visy и не самостоятельная сборка эмулятора shadPS4.

База сборки: **Yharnam Together v1.1.9**, закреплённый commit `77e350743a7cb4524cfcc1782fb6e3af64e25b15`. Обновление до v1.2.0 планируется только с проверкой совместимости. Разрабатываемая ветка: [`feature/seamless-hunt-mainline`](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/tree/feature/seamless-hunt-mainline).

- **Клиент:** нативный Bloodborne PC под Windows 10/11; лаунчер и кооператив из Yharnam Together с проверяемыми улучшениями.
- **Сервер Fornex:** отдельно проверяемая сборка для **Ubuntu 24.04 + Qt 6.8.3**. Рабочий сервер автоматически не изменяется.
- **Совместимость:** подключение к CLS / PS4 / shadPS4 / другим BBPort-клиентам и работа NPC-призывов, дверей и синхронизации **ещё не подтверждены игровыми тестами**.
- **Раздача:** готового публичного установщика пока нет. Никакие игровые файлы, сохранения или чужие личные данные не включаются.

## Благодарности и лицензии

Проект основан на труде команды **Yharnam Together** и других авторов: **deadinside28, Supermedo, 0xCydral (AdrianCsT), shadPS4, Wozzardman/shadp2p, shadNet**, создателей игровых патчей, драйверных библиотек и средств графики. Подробная **англоязычная** таблица авторов, источников, лицензий и того, что действительно используется, находится в [CREDITS.md](CREDITS.md) и [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

**GitHub-репозиторий не становится open source автоматически лишь потому, что он публичен.** Код переносится только с подходящей лицензией или разрешением автора. Исходные права, лицензии и уведомления сохраняются. Названные проекты не являются официальными партнёрами Seamless Hunt.

Bloodborne является интеллектуальной собственностью правообладателей. Это неофициальная фанатская разработка, не связанная с Sony Interactive Entertainment или FromSoftware. Участие и одобрение перечисленных выше разработчиков не подразумеваются.

Для актуального технического состояния и правил сборки используйте [английский README](README.md). Старые описания отдельных портов и их лаунчеров остаются только историческими справочными материалами.
