-- Multi-game trading / sports card database.
-- Rebuilt from scratch by `python -m pokedb build`.

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS coverage_by_language;
DROP VIEW IF EXISTS coverage_by_game;
DROP VIEW IF EXISTS set_release_matrix;
DROP VIEW IF EXISTS sets_overview;
DROP VIEW IF EXISTS cards_full;
DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS set_source_ids;
DROP TABLE IF EXISTS set_sources;
DROP TABLE IF EXISTS sets;
DROP TABLE IF EXISTS languages;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS build_info;

CREATE TABLE games (
    code        TEXT PRIMARY KEY,   -- 'pokemon', 'mtg', 'sports', 'onepiece', ...
    name        TEXT NOT NULL,
    -- Category: tcg | sports | non_sport (Marvel TCs, Carddass, etc.)
    kind        TEXT NOT NULL CHECK (kind IN ('tcg', 'sports', 'non_sport'))
);

CREATE TABLE languages (
    code        TEXT PRIMARY KEY,   -- 'en', 'ja', 'zh-cn', 'zhs', ...
    name_en     TEXT NOT NULL,
    name_native TEXT,
    region      TEXT                -- 'western', 'asian', or NULL
);

-- One row per physical set per game per language.
CREATE TABLE sets (
    set_uid             TEXT PRIMARY KEY,  -- '<game>:<language>:<slug>'
    game                TEXT NOT NULL REFERENCES games(code),
    language            TEXT NOT NULL REFERENCES languages(code),
    name                TEXT,              -- set name in that language / as graded
    name_en             TEXT,              -- English name / translation, where known
    abbreviation        TEXT,              -- set code as printed, e.g. 'SVI', 'BS'
    release_date        TEXT,              -- ISO-8601; may be partial (YYYY or YYYY-MM)
    release_year        INTEGER,
    series_name         TEXT,              -- series / era / block
    sequence            INTEGER,           -- release order within the language
    card_count_official INTEGER,           -- size of the printed set numbering
    card_count_total    INTEGER,           -- including secret rares
    card_count_loaded   INTEGER NOT NULL DEFAULT 0,
    -- Sports-set fields (NULL for TCGs). product_year is the season string.
    manufacturer        TEXT,              -- Topps, Panini, Upper Deck, Skybox, ...
    sport               TEXT,              -- soccer, football, wrestling, ufc, ...
    product_year        TEXT,              -- season: '2025-26', '2024'
    logo_url            TEXT,
    symbol_url          TEXT,
    sources             TEXT NOT NULL,
    source_count        INTEGER NOT NULL
);

-- Provenance: the raw view each source had of a set.
CREATE TABLE set_sources (
    set_uid       TEXT NOT NULL REFERENCES sets(set_uid) ON DELETE CASCADE,
    source        TEXT NOT NULL,
    source_set_id TEXT,
    name          TEXT,
    name_en       TEXT,
    abbreviation  TEXT,
    release_date  TEXT,
    series_name   TEXT,
    sequence      INTEGER,
    matched_by    TEXT,   -- 'seed', 'code', 'name', 'release-date'
    PRIMARY KEY (set_uid, source)
);

-- Generic source identifiers (replaces tcgdex_set_id / pikaqian_set_id columns).
CREATE TABLE set_source_ids (
    set_uid   TEXT NOT NULL REFERENCES sets(set_uid) ON DELETE CASCADE,
    source    TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (set_uid, source)
);

CREATE TABLE cards (
    card_uid       TEXT PRIMARY KEY,  -- '<set_uid>#<number>' or '...#<number>#<parallel>'
    set_uid        TEXT NOT NULL REFERENCES sets(set_uid) ON DELETE CASCADE,
    game           TEXT NOT NULL REFERENCES games(code),
    language       TEXT NOT NULL REFERENCES languages(code),
    number         TEXT NOT NULL,     -- as printed ('001', 'TG12', 'SSL-SM', '38')
    number_prefix  TEXT,
    number_value   INTEGER,
    name           TEXT NOT NULL,     -- card name / display line
    name_en        TEXT,
    name_en_source TEXT,              -- 'source' or 'pokeapi'
    rarity         TEXT,
    card_type      TEXT,
    card_id        TEXT,              -- source identifier
    image_url      TEXT,
    -- Sports-card fields (NULL for most TCGs).
    -- subject_name / notations / print_run are the grading-label parts;
    -- serial is instance data and is not part of card_uid.
    subject_name   TEXT,              -- player / wrestler (grading 'subject')
    parallel       TEXT,              -- 'HALO REF', 'RUBY REF'
    notations      TEXT,              -- comma-separated flags: AUTO,RC,SP
    serial_number  TEXT,              -- '09' when known
    print_run      INTEGER,           -- serial total (15 from 09/15)
    display_name   TEXT,              -- full graded label line
    sources        TEXT NOT NULL
);

CREATE TABLE build_info (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX idx_sets_game         ON sets (game);
CREATE INDEX idx_sets_language     ON sets (language);
CREATE INDEX idx_sets_release      ON sets (release_date);
CREATE INDEX idx_sets_abbreviation ON sets (abbreviation);
CREATE INDEX idx_sets_manufacturer ON sets (manufacturer);
CREATE INDEX idx_sets_sport        ON sets (sport);
CREATE INDEX idx_cards_set         ON cards (set_uid);
CREATE INDEX idx_cards_game        ON cards (game);
CREATE INDEX idx_cards_language    ON cards (language);
CREATE INDEX idx_cards_name        ON cards (name);
CREATE INDEX idx_cards_number      ON cards (number);
CREATE INDEX idx_cards_number_value ON cards (number_value);
CREATE INDEX idx_cards_subject     ON cards (subject_name);
CREATE INDEX idx_cards_parallel    ON cards (parallel);
CREATE INDEX idx_cards_lookup      ON cards (set_uid, number_prefix, number_value);
CREATE INDEX idx_set_source_ids_id ON set_source_ids (source, source_id);

CREATE VIEW cards_full AS
SELECT
    c.game,
    g.name                AS game_name,
    g.kind                AS game_kind,
    c.language,
    l.name_en             AS language_name,
    s.name                AS set_name,
    s.name_en             AS set_name_en,
    s.abbreviation        AS set_abbreviation,
    s.manufacturer,
    s.sport,
    s.product_year,
    s.release_date,
    c.number              AS card_number,
    c.number_prefix,
    c.number_value,
    c.name                AS card_name,
    c.name_en             AS card_name_en,
    c.subject_name,
    c.parallel,
    c.notations,
    c.serial_number,
    c.print_run,
    c.display_name,
    c.rarity,
    s.series_name,
    s.card_count_official AS set_card_count,
    c.card_id,
    c.image_url,
    c.sources,
    s.set_uid
FROM cards c
JOIN sets s      ON s.set_uid = c.set_uid
JOIN games g     ON g.code = c.game
JOIN languages l ON l.code = c.language;

CREATE VIEW sets_overview AS
SELECT
    s.game,
    g.name      AS game_name,
    s.language,
    l.name_en   AS language_name,
    s.name      AS set_name,
    s.name_en   AS set_name_en,
    s.abbreviation AS set_abbreviation,
    s.manufacturer,
    s.sport,
    s.product_year,
    s.release_date,
    s.release_year,
    s.series_name,
    s.card_count_official,
    s.card_count_total,
    s.card_count_loaded,
    s.sources,
    s.set_uid
FROM sets s
JOIN games g     ON g.code = s.game
JOIN languages l ON l.code = s.language;

CREATE VIEW set_release_matrix AS
SELECT
    game,
    COALESCE(name_en, name)          AS set_name_en,
    MIN(release_date)                AS first_release_date,
    COUNT(DISTINCT language)         AS language_count,
    GROUP_CONCAT(DISTINCT language)  AS languages
FROM sets
WHERE COALESCE(name_en, name) IS NOT NULL
GROUP BY game, COALESCE(name_en, name);

CREATE VIEW coverage_by_language AS
SELECT
    l.code                                           AS language,
    l.name_en                                        AS language_name,
    COUNT(s.set_uid)                                 AS sets,
    SUM(CASE WHEN s.card_count_loaded > 0 THEN 1 ELSE 0 END) AS sets_with_cards,
    COALESCE(SUM(s.card_count_loaded), 0)            AS cards,
    MIN(s.release_date)                              AS first_release,
    MAX(s.release_date)                              AS latest_release
FROM languages l
LEFT JOIN sets s ON s.language = l.code
GROUP BY l.code, l.name_en;

CREATE VIEW coverage_by_game AS
SELECT
    g.code                                           AS game,
    g.name                                           AS game_name,
    g.kind                                           AS game_kind,
    COUNT(DISTINCT s.set_uid)                        AS sets,
    COALESCE(SUM(s.card_count_loaded), 0)            AS cards
FROM games g
LEFT JOIN sets s ON s.game = g.code
GROUP BY g.code, g.name, g.kind;
