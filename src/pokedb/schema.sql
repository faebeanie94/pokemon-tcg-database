-- Pokemon TCG multi-language set & card database.
-- Rebuilt from scratch by `python -m pokedb build`.

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS coverage_by_language;
DROP VIEW IF EXISTS set_release_matrix;
DROP VIEW IF EXISTS sets_overview;
DROP VIEW IF EXISTS cards_full;
DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS set_sources;
DROP TABLE IF EXISTS sets;
DROP TABLE IF EXISTS languages;
DROP TABLE IF EXISTS build_info;

CREATE TABLE languages (
    code        TEXT PRIMARY KEY,   -- 'en', 'ja', 'zh-cn', ...
    name_en     TEXT NOT NULL,
    name_native TEXT,
    region      TEXT                -- 'western' or 'asian' release stream
);

-- One row per physical set per language. Rows are merged from every source;
-- see set_sources for what each source contributed.
CREATE TABLE sets (
    set_uid             TEXT PRIMARY KEY,  -- '<language>:<code>'
    language            TEXT NOT NULL REFERENCES languages(code),
    name                TEXT,              -- set name in that language
    name_en             TEXT,              -- English name / translation, where known
    abbreviation        TEXT,              -- set code as printed, e.g. 'SVI', 'SV1S', 'CSM1cC'
    release_date        TEXT,              -- ISO-8601; may be partial (YYYY or YYYY-MM)
    release_year        INTEGER,
    series_name         TEXT,              -- series / era / block
    sequence            INTEGER,           -- release order within the language
    card_count_official INTEGER,           -- size of the printed set numbering
    card_count_total    INTEGER,           -- including secret rares
    card_count_loaded   INTEGER NOT NULL DEFAULT 0,  -- card rows actually present
    tcgdex_set_id       TEXT,
    pikaqian_set_id     TEXT,
    logo_url            TEXT,
    symbol_url          TEXT,
    sources             TEXT NOT NULL,     -- comma separated list of contributing sources
    source_count        INTEGER NOT NULL
);

-- Provenance: the raw view each source had of a set. Useful for auditing
-- disagreements (most often release dates).
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
    matched_by    TEXT,   -- how this row was linked: 'seed', 'code', 'name'
    PRIMARY KEY (set_uid, source)
);

CREATE TABLE cards (
    card_uid      TEXT PRIMARY KEY,  -- '<set_uid>#<number>'
    set_uid       TEXT NOT NULL REFERENCES sets(set_uid) ON DELETE CASCADE,
    language      TEXT NOT NULL REFERENCES languages(code),
    number        TEXT NOT NULL,     -- card number exactly as printed ('001', 'TG12', 'SWSH284')
    number_prefix TEXT,              -- alpha part, for sorting
    number_value  INTEGER,           -- numeric part, for sorting
    name          TEXT NOT NULL,     -- card name in that language
    name_en       TEXT,              -- English name, where the source provides one
    rarity        TEXT,              -- only populated by sources that carry it
    card_type     TEXT,
    card_id       TEXT,              -- source identifier, e.g. 'sv01-001'
    image_url     TEXT,
    sources       TEXT NOT NULL
);

CREATE TABLE build_info (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX idx_sets_language     ON sets (language);
CREATE INDEX idx_sets_release      ON sets (release_date);
CREATE INDEX idx_sets_abbreviation ON sets (abbreviation);
CREATE INDEX idx_cards_set         ON cards (set_uid);
CREATE INDEX idx_cards_language    ON cards (language);
CREATE INDEX idx_cards_name        ON cards (name);
CREATE INDEX idx_cards_number      ON cards (number);

-- Flat, spreadsheet-shaped view: one row per card with its set context.
CREATE VIEW cards_full AS
SELECT
    c.language,
    l.name_en             AS language_name,
    s.name                AS set_name,
    s.name_en             AS set_name_en,
    s.abbreviation        AS set_abbreviation,
    s.release_date,
    c.number              AS card_number,
    c.number_prefix,
    c.number_value,
    c.name                AS card_name,
    c.name_en             AS card_name_en,
    c.rarity,
    s.series_name,
    s.card_count_official AS set_card_count,
    c.card_id,
    c.image_url,
    c.sources,
    s.set_uid
FROM cards c
JOIN sets s      ON s.set_uid = c.set_uid
JOIN languages l ON l.code = c.language;

-- One row per released set in every language.
CREATE VIEW sets_overview AS
SELECT
    s.language,
    l.name_en   AS language_name,
    s.name      AS set_name,
    s.name_en   AS set_name_en,
    s.abbreviation AS set_abbreviation,
    s.release_date,
    s.release_year,
    s.series_name,
    s.card_count_official,
    s.card_count_total,
    s.card_count_loaded,
    s.sources,
    s.set_uid
FROM sets s
JOIN languages l ON l.code = s.language;

-- Which languages a set was released in, keyed by its English name.
CREATE VIEW set_release_matrix AS
SELECT
    COALESCE(name_en, name)          AS set_name_en,
    MIN(release_date)                AS first_release_date,
    COUNT(DISTINCT language)         AS language_count,
    GROUP_CONCAT(DISTINCT language)  AS languages
FROM sets
WHERE COALESCE(name_en, name) IS NOT NULL
GROUP BY COALESCE(name_en, name);

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
