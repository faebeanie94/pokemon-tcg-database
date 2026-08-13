# Sports checklist curation

Sports / entertainment cards (soccer, football, wrestling, UFC, Topps, Panini,
Upper Deck, Skybox) have **no public checklist API**. This project uses curated
data as the default ingestion path (Option A from the multi-game plan).

## Files

| Path | Purpose |
| --- | --- |
| [`data/raw/sports/seed.json`](../data/raw/sports/seed.json) | Built-in seed (Beckham / Michaels / sample football & AEW) |
| `sports_checklists.xlsx` (repo root or `data/`) | Optional operator workbook |
| [`src/pokedb/sources/sports_json.py`](../src/pokedb/sources/sports_json.py) | Loads seed.json |
| [`src/pokedb/sources/sports_xlsx.py`](../src/pokedb/sources/sports_xlsx.py) | Loads the xlsx when present |

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

## Backlog (no API)

Bandai Carddass, Meiji, Marvel trading cards (non–Dice Masters), UFC lines —
same curated-spreadsheet approach when needed. See [DATA_SOURCES.md](DATA_SOURCES.md).
