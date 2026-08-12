"""Source-neutral records that every loader produces."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SetRecord:
    source: str
    language: str
    source_set_id: str | None = None
    name: str | None = None          # name in the language of the set
    name_en: str | None = None       # English name or translation
    abbreviation: str | None = None
    release_date: str | None = None
    series_name: str | None = None
    sequence: int | None = None
    card_count_official: int | None = None
    card_count_total: int | None = None
    logo_url: str | None = None
    symbol_url: str | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.name_en or self.abbreviation or self.source_set_id or "?"


@dataclass(slots=True)
class CardRecord:
    source: str
    language: str
    source_set_id: str
    number: str
    name: str
    name_en: str | None = None
    rarity: str | None = None
    card_type: str | None = None
    card_id: str | None = None
    image_url: str | None = None


@dataclass(slots=True)
class SourceData:
    name: str
    sets: list[SetRecord] = field(default_factory=list)
    cards: list[CardRecord] = field(default_factory=list)
