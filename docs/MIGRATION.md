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

# with parallel / variant:
sports:en:202526toppsmanchesterunitedteamset#38#haloref
```

## Impact

- Every rebuild with the new schema produces new `card_uid` values.
- Grading records that stored the old UID should remap:
  - Prefer looking up by set + number + language + game when possible.
  - Temporary dual-accept: `/api/match` still recognises legacy UIDs without a
    game prefix when pasted as free text (via the query parser).

## Rebuild size notes

| Source | Approx size |
| --- | --- |
| Pokémon (existing) | ~145k cards |
| Scryfall All Cards | ~372 MB download; hundreds of thousands of multilingual rows |
| Full TCGCSV category walk | Large; rate-limit politely (~0.35s between groups) |

Prefer fetching only the games you grade:  
`python -m pokedb fetch --source tcgcsv --game onepiece --game lorcana`

## Licensing

Catalog data and card images from Bandai, Konami, Wizards, Ravensburger, Topps,
Panini, and others are for **internal grading use** unless you hold redistribution
rights. Community APIs often disclaim passing data rights to consumers.
