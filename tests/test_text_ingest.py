from __future__ import annotations

import pytest

from engine.text_ingest import split_into_sections


def test_splits_on_blank_lines():
    text = "line one\nline two\n\nline three\nline four"
    sections = split_into_sections(text)
    assert [s.name for s in sections] == ["section_1", "section_2"]
    assert sections[0].source_text == "line one\nline two"
    assert sections[1].source_text == "line three\nline four"


def test_collapses_multiple_blank_lines_into_one_break():
    text = "a\n\n\n\nb"
    sections = split_into_sections(text)
    assert len(sections) == 2


def test_single_block_with_no_blank_lines():
    text = "just one block\nof several lines\nno breaks"
    sections = split_into_sections(text)
    assert len(sections) == 1
    assert sections[0].name == "section_1"


def test_raises_on_empty_text():
    with pytest.raises(ValueError):
        split_into_sections("   \n\n  ")
