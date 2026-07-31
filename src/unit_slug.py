from __future__ import annotations


def slugify_unit(unit: str) -> str:
    return unit.strip().lower().replace("/", "_")
