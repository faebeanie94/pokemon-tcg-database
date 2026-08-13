# Multi-game data sources

Which categories can be loaded automatically, and which need curation.

## Automated (API / bulk dump)

| Category | Source | Notes |
| --- | --- | --- |
| Pokémon (all languages) | TCGdex + PikaQian + database.xlsx | Existing pipeline |
| Magic: The Gathering (all languages) | Scryfall bulk `All Cards` | Best multilingual coverage |
| Yu-Gi-Oh! | TCGCSV (cat 2) + YGOPRODeck | YGOPRODeck: en/fr/de/it/pt only; no Japanese OCG text |
| One Piece | TCGCSV (cat 68) + apitcg + Bandai JP cardlist | English via TCGCSV; Japanese needs Bandai scrape |
| Lorcana | TCGCSV (cat 71) + Lorcast | English-centric |
| Flesh and Blood | TCGCSV (cat 62) + GoAgain / fab-cube | |
| Weiss Schwarz | TCGCSV (cat 20) | English releases only on TCGplayer |
| Dragon Ball Z (Panini TCG) | TCGCSV (cat 23) | |
| Dragon Ball Super: Masters | TCGCSV (cat 27) | |
| Dragon Ball Super: Fusion World | TCGCSV (cat 80) + apitcg | |
| MetaZoo | TCGCSV (cat 66) | Catalog is static (game discontinued) |
| Warhammer Age of Sigmar Champions | TCGCSV (cat 54) | Card game only — not miniatures |
| Marvel Dice Masters | TCGCSV (cat 18) | Dice + cards, not Marvel trading cards |

TCGCSV base: `https://tcgcsv.com/tcgplayer/` (no API key).

## Sports & manufacturer lines (no catalog API)

Soccer, football, wrestling, UFC, Topps, Panini, Upper Deck, and Skybox checklists
are not published as structured APIs. Ingestion options:

1. **Curated spreadsheets** (default) — `sports_checklists.xlsx` / seed JSON, same
   pattern as `database.xlsx`.
2. TCDB / Beckett scraping (fragile, terms-of-service risk).
3. Commercial catalog vendors (e.g. CardSight).

Sports grading format (operator fields):

| Field | Example |
| --- | --- |
| Set name | `2025-26 TOPPS MANCHESTER UNITED TEAM SET` |
| Card name + parallel | `SIR DAVID BECKHAM - HALO REF.` |
| Number | `38` |

Parallels, inserts (`AUTO`), and serials (`09/15`) are first-class card columns.
`09/15` is a print run, not a Pokémon-style printed total.

## Manual / community-only (backlog)

| Category | Strategy |
| --- | --- |
| Bandai Carddass | Community wiki / spreadsheet |
| Meiji promotional cards | Collector spreadsheets |
| Marvel trading cards (Fleer/Skybox/UD) | Sports-style curation |
| UFC trading cards | Sports-style curation |
| Warhammer (TCGPlayer cats 39–45) | Miniatures/paints/books — **not cards**; skip |

## Language coverage reality

| Claim | Reality |
| --- | --- |
| "All languages" for Magic | Scryfall (~19 languages) |
| "All languages" for Pokémon | TCGdex (16 languages in this repo) |
| "All languages" for Yu-Gi-Oh | YGOPRODeck: five Western languages only |
| Bandai games | English-first; Japanese via official sites |
| Sports cards | Typically English labels; language axis is secondary |

## Licensing

Bandai, Konami, Ravensburger, Wizards, Topps, and Panini assert rights over card
data and images. Community APIs often disclaim redistributing data rights. Fine
for an **internal grading tool**; do not republish catalogs without a license.
