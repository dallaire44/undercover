"""The policy wording and the claims manual, split into numbered sections."""

import re
from functools import cache
from typing import NamedTuple

from fastapi import HTTPException

from backend import db

NAMES = {"policy_wording": "Policy wording", "claims_manual": "Claims manual"}
COMMON = {"the", "and", "for", "with", "what", "when", "how", "are", "was", "does"}
RESULTS = 5
SNIPPET = 240


class Section(NamedTuple):
    document: str
    number: str
    title: str
    body: str

    def heading(self) -> str:
        """Name the section, such as `Claims manual, 9. Repeat claims`."""
        return f"{NAMES[self.document]}, {self.title}"


@cache
def sections(document: str) -> list[Section]:
    """Return a document's sections, split on its `## ` headings."""
    text = (db.DATA / f"{document}.md").read_text(encoding="utf-8")
    found = []
    for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        title, _, body = part.partition("\n")
        found.append(Section(document, title.split(".")[0], title, body.strip()))
    return found


def contents() -> str:
    """List every section of both documents."""
    lines = []
    for document, name in NAMES.items():
        lines.append(f"{name} ({document}):")
        lines.extend(f"- {section.title}" for section in sections(document))
    return "\n".join(lines)


def words(text: str) -> set[str]:
    """Return the words of a text worth searching for."""
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in COMMON}


def score(section: Section, wanted: set[str]) -> tuple[int, int]:
    """Score a section: the query's words it holds, then how often they occur."""
    found = re.findall(r"[a-z0-9]+", section.body.lower() + section.title.lower())
    return len(wanted & set(found)), sum(word in wanted for word in found)


def best_line(section: Section, wanted: set[str]) -> str:
    """Return the line of a section that holds most of the query's words."""
    line = max(section.body.splitlines(), key=lambda line: len(wanted & words(line)))
    return line[:SNIPPET]


def search(query: str) -> str:
    """Return the sections that best match the query, each with its best line."""
    wanted = words(query)
    every = [s for document in NAMES for s in sections(document)]
    ranked = sorted(every, key=lambda s: score(s, wanted), reverse=True)
    matches = [s for s in ranked if score(s, wanted)[0]][:RESULTS]
    if not matches:
        return f"No section matches {query!r}."
    return "\n".join(
        f"{s.heading()} ({s.document}, {s.number}): {best_line(s, wanted)}"
        for s in matches
    )


def read(document: str, number: str) -> str:
    """Return one section, headed with its name, or raise 404."""
    for section in sections(document) if document in NAMES else []:
        if section.number == number:
            return f"{section.heading()}\n\n{section.body}"
    raise HTTPException(404, f"{document} has no section {number}")
