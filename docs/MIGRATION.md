# Card UID migration

## Old format (Pokémon-only)

```
<language>:<set_code>#<number>
en:bs#4
```

## New format (multi-game)

```
<game>:<language>:<set_slug>#<number>
pokemon:en:bs#4
mtg:zhs:lea#1

# with parallel / variant:
sports:en:202526toppsmanchesterunitedteamset#38#haloref
```

Language is 2–3 letters (`en`, `zhs`, `und`), optionally hyphenated (`zh-cn`).

## Impact

- Every rebuild with the new schema produces new `card_uid` values.
- **Grading records should store the new form** going forward.
- Records that still hold the old UID can be remapped by looking up
  set + number + language + game, or by pasting the legacy UID into
  `/api/match` as free text. The matcher still recognises `en:bs#4` and
  resolves it to `pokemon:en:bs#4`.

## Rebuild size notes

| Source | Approx size |
| --- | --- |
| Pokémon (existing) | ~145k cards |
| Scryfall All Cards | ~372 MB download; hundreds of thousands of multilingual rows |
| Full TCGCSV category walk | Large; rate-limit politely |

Prefer fetching only the games you grade:

```bash
PYTHONPATH=src python3 -m pokedb fetch --source tcgcsv --game onepiece --game lorcana
PYTHONPATH=src python3 -m pokedb build
pnpm build:index
```

| Script | Behaviour |
| --- | --- |
| `pnpm refresh` | **TCGdex only** (Pokémon) — default, stays fast |
| `pnpm refresh:games` | TCGdex + TCGCSV + YGOPRODeck + Lorcast + GoAgain + apitcg (no Scryfall) |
| `pnpm fetch:mtg` | Scryfall bulk only (large); then `build` + `build:index` |
| `pnpm fetch:onepiece` | TCGCSV + apitcg for One Piece |

Extra sources are also opt-in via `python -m pokedb update --source …` or
`pokedb fetch --source …`. See [DATA_SOURCES.md](DATA_SOURCES.md).

## Licensing

Catalog data and card images from Bandai, Konami, Wizards, Ravensburger, Topps,
Panini, and others are for **internal grading use** unless you hold
redistribution rights. Community APIs often disclaim passing data rights to
consumers. See [DATA_SOURCES.md](DATA_SOURCES.md).
