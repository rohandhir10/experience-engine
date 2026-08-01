"""Output normalization, so formatting can't leak which system produced
what. Every system's output is reduced to the same shape: a list of plain
section texts — no [section] headers, no quotes, no markdown, uniform
whitespace. If AURA's output kept its line-break style while Google
Translate's arrived as one run-on paragraph, reviewers would identify
systems by typography instead of judging the writing.
"""
from __future__ import annotations

import re

_SECTION_HEADER_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
_MD_FENCE_RE = re.compile(r"^```.*$")
_QUOTE_WRAP_RE = re.compile(r'^["\'“‘](.*)["\'”’]$', re.DOTALL)


def normalize_section(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _SECTION_HEADER_RE.match(line) or _MD_FENCE_RE.match(line):
            continue
        line = line.lstrip("-*>• ").strip()
        match = _QUOTE_WRAP_RE.match(line)
        if match:
            line = match.group(1).strip()
        line = re.sub(r"[ \t]+", " ", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def normalize_sections(sections: list[str]) -> list[str]:
    normalized = [normalize_section(s) for s in sections]
    return [s for s in normalized if s]
