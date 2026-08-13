"""Shared helpers for mapping TCGplayer extendedData into card fields."""

from __future__ import annotations

from typing import Any


def extended_map(product: dict[str, Any]) -> dict[str, str]:
    """Flatten TCGplayer extendedData [{name, value}, ...] into a dict."""
    out: dict[str, str] = {}
    for item in product.get("extendedData") or []:
        name = str(item.get("name") or "").strip().lower()
        value = item.get("value")
        if name and value is not None:
            out[name] = str(value).strip()
    return out


def pick_number(ext: dict[str, str], product: dict[str, Any]) -> str | None:
    for key in ("number", "card number", "collector number", "#"):
        if ext.get(key):
            return ext[key]
    # Some products put the number in the name as "Card Name - 001/198"
    name = str(product.get("name") or "")
    if " - " in name:
        tail = name.rsplit(" - ", 1)[-1].strip()
        if "/" in tail:
            return tail.split("/", 1)[0].strip()
        if tail.replace(".", "").isalnum() and any(c.isdigit() for c in tail):
            return tail
    return None


def pick_rarity(ext: dict[str, str]) -> str | None:
    for key in ("rarity", "rarity type"):
        if ext.get(key):
            return ext[key]
    return None
