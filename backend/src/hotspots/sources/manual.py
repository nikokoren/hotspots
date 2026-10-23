"""Hand-maintained list of erupting volcanoes (eruptions.txt in the repo root).

A stopgap while GVP's eruption database is not updated and its weekly report is not
machine-readable for us: once a week, paste the volcano names from the GVP/USGS
Weekly Volcanic Activity Report into the file and commit it. One volcano per line;
anything after a tab, a comma or an opening parenthesis is ignored, so report lines
like "Dukono, Halmahera (Indonesia)" and rows copied from the report's table (tab-
separated, header row included) work as pasted. Lines starting with # are comments.

Names are matched to the catalogue ignoring case, accents and punctuation; GVP's
inverted names ("Ruiz, Nevado del") also match in natural order ("Nevado del Ruiz").
The list counts only while fresh: its last git commit (or file time outside git) must
be within the configured number of days, so a forgotten update cannot keep plumes up.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from hotspots.models import Volcano


@dataclass
class ManualList:
    ids: set[str] = field(default_factory=set)
    unmatched: list[str] = field(default_factory=list)
    ambiguous: dict[str, list[str]] = field(default_factory=dict)  # line → matched volcano ids


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def name_index(volcanoes: list[Volcano]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for v in volcanoes:
        keys = {normalize(v.name)}
        if "," in v.name:
            head, tail = v.name.split(",", 1)
            keys.add(normalize(f"{tail} {head}"))
        for k in keys:
            index.setdefault(k, set()).add(v.volcano_id)
    return index


def parse(text: str, volcanoes: list[Volcano]) -> ManualList:
    index = name_index(volcanoes)
    out = ManualList()
    for raw in text.splitlines():
        line = raw.split("\t")[0].strip()
        if not line or line.startswith("#") or (line.lower() == "name" and "\t" in raw):
            continue  # blank, comment, or the header row of a pasted table
        # Whole line first (catalogue names can contain commas), then the part before
        # the first comma or parenthesis.
        candidates = [line.split("(")[0], re.split(r"[,(]", line)[0]]
        ids = next((index[k] for k in map(normalize, candidates) if k in index), None)
        if ids is None:
            out.unmatched.append(line)
            continue
        if len(ids) > 1:
            out.ambiguous[line] = sorted(ids)  # all kept: only those with heat markers show
        out.ids |= ids
    return out


def last_updated(path: Path) -> datetime | None:
    """Time of the file's last git commit; file modification time outside a git checkout."""
    if not path.exists():
        return None
    try:
        stamp = subprocess.run(["git", "log", "-1", "--format=%cI", "--", path.name], cwd=path.parent,
                               capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        if stamp:
            return datetime.fromisoformat(stamp).astimezone(timezone.utc)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
