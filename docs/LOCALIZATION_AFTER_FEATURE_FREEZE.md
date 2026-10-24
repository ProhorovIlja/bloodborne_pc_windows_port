# Localization after feature freeze (deferred, not activated)

**Product order:** complete the native Windows engine, launcher, gameplay/BBSC interoperability, diagnostics, update system and performance work **before** doing full translations. Do **not** spend engineering time translating unfinished UI strings or changing the game's original language resources during the online-port milestone.

## Sources and supported languages

- Official PlayStation European Bloodborne storefront lists **14 screen languages** (text/UI/subtitles): Danish, Dutch, English, Finnish, French (France), German, Italian, Norwegian, Polish, Portuguese (Portugal), Russian, Spanish, Swedish and Turkish. Spoken-language choices differ. Source: https://store.playstation.com/en-se/product/EP9000-CUSA00207_00-BLOODBORNE0000EU
- deadinside28's Bloodborne native Linux port 0.6 documents a **21-language selector** for text in the 1.09 game. This is an **upstream implementation claim**, not a guarantee that every retail regional dump includes every resource. Sources: https://github.com/deadinside28/bloodborne_pc and https://github.com/deadinside28/bloodborne_pc/issues/249
- Other retail regions can have additional Japanese, Chinese or Korean text resources, subject to game asset availability and version/region checks. Source for region caveat: https://github.com/deadinside28/bloodborne_pc/issues/96
- Supermedo has a 13-language launcher and deadinside28 has English/Russian/pt-BR/zh-CN already. Review strings, translated descriptions, fonts and licenses before choosing a catalog format. This project still has no completed localization layer.

## Target after all features stabilize

**English default**, Russian first, then primary audience languages as complete catalogs (not partially localized navigation). The final exact supported set must be based on actual game resources and the agreed localization QA budget. Prefer game text language matching the user's game setting, with an **independent launcher language** choice and English fallback.

1. Assign stable translation keys to every launcher and in-game mod menu label, tooltip, status, warning, settings search label, first-run screen, updater and diagnostic explanation. Never translate config keys, executable commands, log fields, network or protocol tokens.
2. Localize only **new/custom mod items, bell descriptions, NPC/menu additions, gameplay messages and QoL texts**, not redistributing any proprietary original-game text or assets. Preserve the game's existing official localized item names and terminology.
3. Make the installed game's text locale the default for mod strings, with fallback to English only for missing custom keys. Ensure mod menu and launcher value types/units, interpolation fields and formatting remain correct.
4. Review CJK/extended Latin glyph availability, UI width, sorting and line breaks. Include right-to-left interface support **only if** an Arabic/Hebrew catalog is actually funded/tested rather than publishing broken RTL.
5. Test each locale in a real Windows package and in-game: onboarding, account errors, party/bell UI, passwords, item pickup/description, deaths/respawn, options, diagnostics, backup/rollback. Pseudolocale and placeholder checks run in CI.
6. Keep translations separate from core C++ behavior and versioned with stable IDs. Later updates adding features must update relevant locale keys in the same change; a "frozen" release does not mean never maintaining languages.

## Present status

Localization intentionally **not implemented** in this branch. The current launcher is English, search now matches Unicode text, and existing game/localized assets are left untouched. Revisit only after production-ready feature freeze and end-to-end BBSC compatibility are demonstrated.
