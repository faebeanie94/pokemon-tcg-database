"""Link the same physical set (and card) across sources.

Each source names sets differently: ``database.xlsx`` uses collector
abbreviations (``BS``, ``DP1``, ``CSM1cC``), TCGdex uses its own identifiers
(``base1``, ``sv01``, ``SV1S``) plus an official abbreviation, and pikaqian uses
lower-cased Chinese set codes (``csm1cc``). Codes are therefore folded to a
common form and compared first; set names are used as a fallback, guarded by
release year so unrelated sets with similar names are never merged.

Matching is scoped by **game** and language so a Magic set coded ``BS`` never
collides with Pokémon Base Set.

A source may only contribute one row to a canonical set. That keeps genuinely
distinct printings that share a code (``Base Set`` and ``Base Set
(Shadowless)`` are both ``BS``) as separate rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .normalize import (
    normalize_code,
    normalize_name,
    release_year,
    slugify,
    split_number,
)
from .records import CardRecord, SetRecord

CODE = "code"
NAME = "name"
# Codes are reused across eras (database.xlsx calls Gym Heroes 'G1', TCGdex
# calls Generations 'G1'), so even a code match has to agree on release year.
MAX_YEAR_GAP = {CODE: 3, NAME: 2}


def parallel_slug(parallel: str | None) -> str | None:
    """Fold a parallel label into a stable card_uid segment."""
    if not parallel:
        return None
    return slugify(parallel, fallback="") or None


def make_card_uid(set_uid: str, number: str, parallel: str | None = None) -> str:
    base = f"{set_uid}#{number}"
    slug = parallel_slug(parallel)
    return f"{base}#{slug}" if slug else base


@dataclass
class CanonicalSet:
    game: str
    language: str
    set_uid: str = ""
    records: dict[str, SetRecord] = field(default_factory=dict)
    matched_by: dict[str, str] = field(default_factory=dict)

    def add(self, record: SetRecord, matched_by: str) -> None:
        self.records[record.source] = record
        self.matched_by[record.source] = matched_by

    def has_source(self, source: str) -> bool:
        return source in self.records

    def ordered(self, source_order: list[str]) -> list[SetRecord]:
        return [self.records[name] for name in source_order if name in self.records]

    def first(self, source_order: list[str], attribute: str):
        for record in self.ordered(source_order):
            value = getattr(record, attribute)
            if value not in (None, ""):
                return value
        return None

    def display_name(self, source_order: list[str]) -> str:
        return (
            self.first(source_order, "name")
            or self.first(source_order, "name_en")
            or self.first(source_order, "abbreviation")
            or "?"
        )

    @property
    def years(self) -> list[int]:
        return [
            year
            for year in (release_year(record.release_date) for record in self.records.values())
            if year
        ]


class SetRegistry:
    """Groups incoming SetRecords into canonical sets, one per game+language."""

    def __init__(self, source_order: list[str]) -> None:
        self.source_order = source_order
        self.canonical: list[CanonicalSet] = []
        # (game, language, kind, key) -> CanonicalSet
        self._by_key: dict[tuple[str, str, str, str], CanonicalSet] = {}
        # (source, game, language, code) -> CanonicalSet
        self._by_source_set: dict[tuple[str, str, str, str], CanonicalSet] = {}
        self.notes: list[str] = []

    def add(self, record: SetRecord) -> CanonicalSet:
        code_keys = _unique(
            normalize_code(record.source_set_id), normalize_code(record.abbreviation)
        )
        name_keys = _unique(normalize_name(record.name), normalize_name(record.name_en))

        target, matched_by = self._find(record, code_keys, name_keys)
        if target is None:
            target = CanonicalSet(game=record.game, language=record.language)
            self.canonical.append(target)
            matched_by = "seed"

        target.add(record, matched_by)
        for key in code_keys:
            self._by_key.setdefault((record.game, record.language, CODE, key), target)
        for key in name_keys:
            self._by_key.setdefault((record.game, record.language, NAME, key), target)
        if record.source_set_id:
            source_key = (
                record.source,
                record.game,
                record.language,
                normalize_code(record.source_set_id) or "",
            )
            self._by_source_set.setdefault(source_key, target)
        return target

    def _find(
        self, record: SetRecord, code_keys: list[str], name_keys: list[str]
    ) -> tuple[CanonicalSet | None, str]:
        year = release_year(record.release_date)
        for kind, keys in ((CODE, code_keys), (NAME, name_keys)):
            for key in keys:
                candidate = self._by_key.get((record.game, record.language, kind, key))
                if candidate is None or candidate.has_source(record.source):
                    continue
                if self._year_conflict(year, candidate.years, MAX_YEAR_GAP[kind]):
                    self.notes.append(
                        f"{kind} match '{key}' rejected on release year: {record.game}/"
                        f"{record.language} '{record.display_name}' ({record.release_date}) vs "
                        f"'{candidate.display_name(self.source_order)}' "
                        f"({candidate.first(self.source_order, 'release_date')})"
                    )
                    continue
                return candidate, kind
        return None, "seed"

    @staticmethod
    def _year_conflict(year: int | None, others: list[int], max_gap: int) -> bool:
        if not year or not others:
            return False
        return min(abs(year - other) for other in others) > max_gap

    def link_by_unique_release_date(self) -> int:
        """Link leftover sets that are alone on their release date.

        The Japanese and Chinese sheets of database.xlsx hold English
        translations, which share no characters with the native set names
        TCGdex returns, so they cannot be matched on name. When a language has
        exactly one unlinked set from each of two sources on the same release
        date, they must be the same set.
        """
        merged = 0
        by_date: dict[tuple[str, str, str], list[CanonicalSet]] = {}
        for canonical in self.canonical:
            if len(canonical.records) != 1:
                continue
            date = canonical.first(self.source_order, "release_date")
            if date and len(date) == 10:
                by_date.setdefault((canonical.game, canonical.language, date), []).append(
                    canonical
                )

        for candidates in by_date.values():
            if len(candidates) != 2:
                continue
            first, second = candidates
            if set(first.records) & set(second.records):
                continue
            keep, absorb = sorted(
                candidates, key=lambda item: self.source_order.index(next(iter(item.records)))
            )
            self._merge(keep, absorb, "release-date")
            merged += 1
        if merged:
            self.canonical = [item for item in self.canonical if item.records]
        return merged

    def _merge(self, keep: CanonicalSet, absorb: CanonicalSet, matched_by: str) -> None:
        for record in absorb.records.values():
            keep.add(record, matched_by)
        for key, canonical in self._by_key.items():
            if canonical is absorb:
                self._by_key[key] = keep
        for key, canonical in self._by_source_set.items():
            if canonical is absorb:
                self._by_source_set[key] = keep
        absorb.records.clear()

    def assign_uids(self) -> None:
        used: set[str] = set()
        for canonical in self.canonical:
            code = (
                canonical.first(self.source_order, "abbreviation")
                or canonical.first(self.source_order, "source_set_id")
                or canonical.first(self.source_order, "name_en")
                or canonical.first(self.source_order, "name")
                or "set"
            )
            base = f"{canonical.game}:{canonical.language}:{slugify(str(code))}"
            # Codes are reused across eras, so a colliding set is disambiguated
            # by its release year: that keeps identifiers stable between builds
            # regardless of the order the sources were processed in.
            uid = base
            if uid in used:
                year = release_year(canonical.first(self.source_order, "release_date"))
                uid = f"{base}-{year}" if year else base
            counter = 2
            while uid in used:
                uid = f"{base}-{counter}"
                counter += 1
            used.add(uid)
            canonical.set_uid = uid

    def resolve_set_uid(
        self, source: str, game: str, language: str, source_set_id: str
    ) -> str | None:
        canonical = self._by_source_set.get(
            (source, game, language, normalize_code(source_set_id) or "")
        )
        return canonical.set_uid if canonical else None


def merge_cards(
    cards: list[CardRecord],
    registry: SetRegistry,
    source_order: list[str],
) -> tuple[list[dict], list[CardRecord]]:
    """Collapse card rows onto canonical sets.

    One row per (set, number, parallel) — a base printing and its Halo Ref
    parallel are distinct cards.
    """
    order = {name: index for index, name in enumerate(source_order)}
    merged: dict[tuple[str, str, str], dict] = {}
    orphans: list[CardRecord] = []

    for record in sorted(cards, key=lambda item: order.get(item.source, len(order))):
        set_uid = registry.resolve_set_uid(
            record.source, record.game, record.language, record.source_set_id
        )
        if set_uid is None:
            orphans.append(record)
            continue

        prefix, value = split_number(record.number)
        pslug = parallel_slug(record.parallel) or ""
        merge_key = (set_uid, _number_key(record.number, prefix, value), pslug)
        existing = merged.get(merge_key)
        if existing is None:
            display = record.display_name or record.name
            merged[merge_key] = {
                "card_uid": make_card_uid(set_uid, record.number, record.parallel),
                "set_uid": set_uid,
                "game": record.game,
                "language": record.language,
                "number": record.number,
                "number_prefix": prefix,
                "number_value": value,
                "name": record.name,
                "name_en": record.name_en,
                "name_en_source": "source" if record.name_en else None,
                "rarity": record.rarity,
                "card_type": record.card_type,
                "card_id": record.card_id,
                "image_url": record.image_url,
                "subject_name": record.subject_name,
                "parallel": record.parallel,
                "notations": record.notations,
                "serial_number": record.serial_number,
                "print_run": record.print_run,
                "display_name": display,
                "sources": record.source,
            }
            continue

        for attribute in (
            "name_en",
            "rarity",
            "card_type",
            "card_id",
            "image_url",
            "subject_name",
            "notations",
            "serial_number",
            "print_run",
            "display_name",
        ):
            if not existing.get(attribute):
                existing[attribute] = getattr(record, attribute)
                if attribute == "name_en" and existing[attribute]:
                    existing["name_en_source"] = "source"
        if record.source not in existing["sources"].split(","):
            existing["sources"] += f",{record.source}"

    return list(merged.values()), orphans


def _number_key(number: str, prefix: str | None, value: int | None) -> str:
    if value is None:
        return normalize_code(number) or number.lower()
    return f"{prefix or ''}{value}"


def _unique(*values: str | None) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
