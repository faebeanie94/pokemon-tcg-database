# Sports checklist curation

Sports / entertainment cards (soccer, football, wrestling, UFC, Topps, Panini,
Upper Deck, Skybox) have **no public checklist API**. This project uses curated
data as the default ingestion path.

## Files

| Path | Purpose |
| --- | --- |
| [`data/raw/sports/seed.json`](../data/raw/sports/seed.json) | Built-in seed (grading examples + manufacturer coverage) |
| `sports_checklists.xlsx` (repo root or `data/`) | Optional operator workbook |
| [`src/pokedb/sources/sports_json.py`](../src/pokedb/sources/sports_json.py) | Loads seed.json |
| [`src/pokedb/sources/sports_xlsx.py`](../src/pokedb/sources/sports_xlsx.py) | Loads the xlsx when present |

## Seed coverage

The tracked seed is a starter checklist for operators, not a complete catalog:

| Set | Manufacturer | Sport | Notes |
| --- | --- | --- | --- |
| 2025-26 Topps Manchester United Team Set | Topps | soccer | Beckham #38 base + Halo Ref |
| 2024 Panini Flawless WWE | Panini | wrestling | Michaels SSL-SM + Undertaker auto |
| 2025 Topps Chrome Football | Topps | football | Mahomes + Stroud RC parallels |
| 2026 Upper Deck AEW Wrestling | Upper Deck | wrestling | CM Punk + MJF auto |
| 2024 Panini Prizm Soccer | Panini | soccer | Messi / Mbappé parallels |
| 1996-97 Skybox Premium Basketball | Skybox | basketball | Jordan + Kobe RC (manufacturer tag) |
| 2024 Topps Chrome UFC | Topps | ufc | McGregor + Makhachev auto |

Grow this file (or the xlsx) as operators need more releases. After editing:

```bash
PYTHONPATH=src python3 -m pokedb build && pnpm build:index
```

## seed.json shape

```json
{
  "sets": [
    {
      "id": "2024-panini-flawless-wwe",
      "name": "2024 PANINI FLAWLESS WWE",
      "manufacturer": "Panini",
      "sport": "wrestling",
      "product_year": "2024",
      "release_date": "2024-11-15"
    }
  ],
  "cards": [
    {
      "set_id": "2024-panini-flawless-wwe",
      "number": "SSL-SM",
      "subject_name": "SHAWN MICHAELS",
      "notations": "AUTO",
      "parallel": "RUBY REF",
      "serial_number": "09",
      "print_run": 15,
      "display_name": "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15"
    }
  ]
}
```

## xlsx columns

`manufacturer`, `sport`, `season` / `product_year`, `set_name`, `subject_name`,
`parallel`, `notations`, `number`, `serial_number`, `print_run`, `display_name`.

## Grading fields

Operators send three fields to `/api/match` with `game: "sports"`:

1. **Set name** — full title, e.g. `2025-26 TOPPS MANCHESTER UNITED TEAM SET`
2. **Card name + parallel** — e.g. `SIR DAVID BECKHAM - HALO REF.`
3. **Number** — e.g. `38` or `SSL-SM`

`09/15` in the name line is a **print run / serial**, not a Pokémon printed total.

## Adding a new release

1. Append the set and cards to `seed.json` or the xlsx.
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
