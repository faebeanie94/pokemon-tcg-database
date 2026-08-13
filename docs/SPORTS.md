# Sports checklist curation

Sports / entertainment cards (soccer, football, wrestling, UFC, Topps, Panini,
Upper Deck, Skybox) have **no public checklist API**. This project uses a curated
spreadsheet spine plus optional automated dumps.

## Files

| Path | Purpose |
| --- | --- |
| [`sources/sports_database.xlsx`](../sources/sports_database.xlsx) | **Spine** — sets (season, manufacturer, sport, set name) |
| [`sources/sports_cards.xlsx`](../sources/sports_cards.xlsx) | Checklist rows for those sets |
| [`data/raw/sports/seed.json`](../data/raw/sports/seed.json) | Built-in seed (grading examples + manufacturer coverage) |
| [`sources/sports_checklists.xlsx`](../sources/sports_checklists.xlsx) | Optional combined operator workbook (template shipped) |
| `data/raw/tcdb/*.json` | Normalized TCDB dumps (via `apis/tcdb_fetch.py`) |
| `data/raw/beckett/*.json` | Normalized Beckett article dumps (via `apis/beckett_fetch.py`) |

Load precedence within sports (earlier wins on conflicts):

1. `sports_database.xlsx` + `sports_cards.xlsx`
2. `seed.json`
3. `sports_checklists.xlsx`
4. TCDB dumps
5. Beckett dumps

## Regenerating the spine seed

```bash
python3 scripts/seed_sports_xlsx.py
python3 scripts/create_sports_checklists_template.py   # blank+example workbook
```

`seed_sports_xlsx.py` syncs `data/raw/sports/seed.json` into
`sources/sports_database.xlsx` and `sources/sports_cards.xlsx`.

## Seed / spine coverage

| Set | Manufacturer | Sport | Notes |
| --- | --- | --- | --- |
| 2025-26 Topps Manchester United Team Set | Topps | soccer | Beckham #38 base + Halo Ref + more |
| 2024 Panini Flawless WWE | Panini | wrestling | Michaels SSL-SM + Undertaker / Cena |
| 2025 Topps Chrome Football | Topps | football | Mahomes + Stroud RC + Hurts |
| 2026 Upper Deck AEW Wrestling | Upper Deck | wrestling | CM Punk + MJF + Ospreay |
| 2024 Panini Prizm Soccer | Panini | soccer | Messi / Mbappé / Haaland |
| 1996-97 Skybox Premium Basketball | Skybox | basketball | Jordan + Kobe / Iverson RC |
| 2024 Topps Chrome UFC | Topps | ufc | McGregor + Makhachev + Volkanovski |
| 2024 Panini Donruss Football | Panini | football | Allen + Caleb Williams RC |
| 2025 Topps UEFA Club Competitions | Topps | soccer | Vinicius + Bellingham |
| 1989 Bandai Carddass DBZ Part 1 | Bandai | carddass | Phase 5 sample |
| 1998 Meiji Pokemon Get Card | Meiji | promo | Phase 5 sample |
| 1992 Marvel Universe Series 1 | Impel | marvel | Phase 5 sample (not Dice Masters) |

After editing:

```bash
PYTHONPATH=src python3 -m pokedb build && pnpm build:index
```

## sports_database.xlsx columns

`season` / `product_year`, `manufacturer`, `sport`, `set_name`, `release_date`,
optional `source_set_id`, `language`.

## sports_cards.xlsx columns

`set_id` or `set_name`, `number`, `subject`, `parallel`, `variant_tags` /
`notations`, optional `serial_number`, `serial_total` / `print_run`,
`display_name`.

## TCDB / Beckett adapters

```bash
python3 apis/tcdb_fetch.py --from-file path/to/dump.json
python3 apis/beckett_fetch.py --from-file path/to/article.json
PYTHONPATH=src python3 -m pokedb fetch --source tcdb   # prints staging help
PYTHONPATH=src python3 -m pokedb fetch --source beckett
```

Live HTML scraping is **not** implemented (fragile markup / ToS). Drop normalized
JSON into `data/raw/tcdb/` or `data/raw/beckett/` and rebuild. Curated xlsx wins
on set names; automated sources fill card completeness.

## Manufacturer coverage

| Manufacturer / category | Ingestion path |
| --- | --- |
| Topps (soccer, football, wrestling) | curated xlsx / seed + TCDB + Beckett |
| Panini (soccer, football, wrestling, UFC) | curated xlsx / seed + TCDB + Beckett |
| Upper Deck (wrestling, UFC, Marvel) | curated + Beckett |
| Skybox | curated (vintage; no API) |
| Marvel (non-TCG trading cards) | curated / Beckett non-sports |

## Grading fields

Operators send three fields to `/api/match` with `game: "sports"`:

1. **Set name** — full title, e.g. `2025-26 TOPPS MANCHESTER UNITED TEAM SET`
2. **Card name + parallel** — e.g. `SIR DAVID BECKHAM - HALO REF.`
3. **Number** — e.g. `38` or `SSL-SM`

`09/15` in the name line is a **print run / serial**, not a Pokémon printed total.

## Adding a new release

1. Append the set to `sports_database.xlsx` and cards to `sports_cards.xlsx`
   (or extend `seed.json` / drop a TCDB/Beckett JSON).
2. Run `PYTHONPATH=src python3 -m pokedb build && pnpm build:index`.
3. Verify with the operator console (Game → Sports) or:

```bash
curl -s -X POST http://localhost:3000/api/match \
  -H 'content-type: application/json' \
  -d '{"game":"sports","set":"...","name":"...","number":"..."}'
```

## Phase 5 backlog (no API)

Bandai Carddass, Meiji, Marvel trading cards (non–Dice Masters) — same curated
spreadsheet approach when needed. See [DATA_SOURCES.md](DATA_SOURCES.md).
