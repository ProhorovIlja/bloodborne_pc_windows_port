"""Side-effect-free, Unicode-aware search for launcher settings.

Rows are (tab title, visible control label). The launcher supplies these from
its live Tk UI so no second list of settings can go stale. Never index input
field values, which can contain passwords, character names or party codes.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

_TOKEN = re.compile(r"[^\W_]+(?:_[^\W_]+)*", flags=re.UNICODE)


def search_entries(entries: Sequence[tuple[str, str]], query: str, *, limit: int = 35) -> list[int]:
    """Return indices of relevant entries, most useful first, with stable ties.

    Whitespace and punctuation in the query are treated as word separators.
    The actual launcher remains English for now; Unicode matching makes the
    search engine ready for the *later* translation phase.
    """
    if not isinstance(query, str) or not 1 <= limit <= 100:
        return []
    words = _TOKEN.findall(query.casefold())
    if not words:
        return []
    phrase = " ".join(words)
    hits: list[tuple[int, int]] = []
    unique: set[tuple[str, str]] = set()
    for i, row in enumerate(entries):
        if len(row) != 2:
            continue
        tab, label = row
        if not isinstance(tab, str) or not isinstance(label, str):
            continue
        key = (tab.casefold().strip(), label.casefold().strip())
        if not key[1] or key in unique:
            continue
        unique.add(key)
        tab_text, label_text = key
        normalized = " ".join(_TOKEN.findall(label_text))
        combined = " ".join((tab_text, normalized))
        if normalized.startswith(phrase):
            score = 0
        elif phrase in normalized:
            score = 1
        elif all(word in normalized for word in words):
            score = 2
        elif all(word in combined for word in words):
            score = 3
        else:
            continue
        hits.append((score, i))
    hits.sort()
    return [i for _, i in hits[:limit]]
