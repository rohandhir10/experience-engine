"""Tests for engine/verify.py::check_cross_language_fidelity — the one
check in verify.py that compares the shipped line against the actual
source-language text directly, rather than against the Translator's own
English anchor the way every other check there does
(docs/CAPABILITY_MATRIX.md, "Cross-language emotional fidelity
verification"). Unlike tests/test_verify.py, this DOES involve an LLM
(a FakeClient standing in for one) — that's the whole point of this
check existing.
"""
from __future__ import annotations

from engine.models import Deviation
from engine.verify import check_cross_language_fidelity, verify_result

from .test_verify import ANCHOR, _section


class FakeFidelityClient:
    def __init__(self, response: dict | None = None, raises: Exception | None = None):
        self.response = response or {"emotional_fidelity": "preserved"}
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append((system, user))
        if self.raises:
            raise self.raises
        return self.response


def test_preserved_returns_no_finding():
    client = FakeFidelityClient({"emotional_fidelity": "preserved"})
    finding = check_cross_language_fidelity(
        client, "उदास शाम", "A quiet, sad evening", "Hindi", "English", "verse_1"
    )
    assert finding is None


def test_flattened_returns_a_warning_finding():
    client = FakeFidelityClient(
        {
            "emotional_fidelity": "flattened",
            "concern": "The source's grief reads as mere wistfulness here.",
            "confidence": 0.8,
        }
    )
    finding = check_cross_language_fidelity(
        client, "उदास शाम", "A nice evening", "Hindi", "English", "verse_1"
    )
    assert finding is not None
    assert finding.severity == "warning"
    assert finding.section == "verse_1"
    assert finding.law == "Cross-language emotional fidelity"
    assert "FLATTENED" in finding.detail
    assert "grief reads as mere wistfulness" in finding.detail
    assert "80%" in finding.detail


def test_amplified_and_inverted_also_produce_findings():
    for kind in ("amplified", "inverted"):
        client = FakeFidelityClient({"emotional_fidelity": kind, "concern": "test"})
        finding = check_cross_language_fidelity(
            client, "source", "final", "Japanese", "English", "chorus"
        )
        assert finding is not None
        assert kind.upper() in finding.detail


def test_unrecognized_response_value_returns_no_finding():
    client = FakeFidelityClient({"emotional_fidelity": "something_unexpected"})
    finding = check_cross_language_fidelity(
        client, "source", "final", "Korean", "English", "verse_1"
    )
    assert finding is None


def test_missing_key_returns_no_finding():
    client = FakeFidelityClient({})
    finding = check_cross_language_fidelity(
        client, "source", "final", "Spanish", "English", "verse_1"
    )
    assert finding is None


def test_call_failure_degrades_to_no_finding_not_a_crash():
    client = FakeFidelityClient(raises=RuntimeError("provider timeout"))
    finding = check_cross_language_fidelity(
        client, "source", "final", "Urdu", "English", "verse_1"
    )
    assert finding is None


def test_prompt_carries_the_real_source_text_and_final_line():
    client = FakeFidelityClient()
    check_cross_language_fidelity(
        client, "यह मेरा दिल है", "This is my heart", "Hindi", "English", "verse_1"
    )
    system, user = client.calls[0]
    assert "यह मेरा दिल है" in user
    assert "This is my heart" in user
    assert "Hindi" in system


# ---------------------------------------------------------------------------
# verify_result integration
# ---------------------------------------------------------------------------


def _result_dict_with_source(source_text: str = "उदास शाम", final_line: str = "A quiet evening"):
    section = _section(
        final_line,
        [
            Deviation(
                fragment_original="sad",
                fragment_adapted="quiet",
                justification="Softer register fits the melody better.",
                dimension="natural_target_language",
            )
        ],
    )
    return {
        "sections": [section.model_dump()],
        "source_sections": [{"name": "verse_1", "source_text": source_text}],
        "source_language": "Hindi",
        "target_language": "English",
    }


def test_verify_result_without_client_never_calls_the_check():
    # Default behavior (no client) must be byte-for-byte what it was
    # before this feature existed - every pre-existing caller of
    # verify_result passes no client and must see no change.
    result_dict = _result_dict_with_source()
    report = verify_result(result_dict)
    fidelity_findings = [
        f for f in report.all_findings if f.law == "Cross-language emotional fidelity"
    ]
    assert fidelity_findings == []


def test_verify_result_with_client_surfaces_a_warning_not_an_error():
    client = FakeFidelityClient(
        {"emotional_fidelity": "flattened", "concern": "test concern"}
    )
    result_dict = _result_dict_with_source()
    report = verify_result(result_dict, client=client)

    fidelity_findings = [
        f for f in report.all_findings if f.law == "Cross-language emotional fidelity"
    ]
    assert len(fidelity_findings) == 1
    assert fidelity_findings[0].severity == "warning"
    # A warning must never fail the report - only "error" severity does.
    assert not any(f.severity == "error" for f in fidelity_findings)


def test_verify_result_with_client_and_preserved_response_adds_nothing():
    client = FakeFidelityClient({"emotional_fidelity": "preserved"})
    result_dict = _result_dict_with_source()
    report = verify_result(result_dict, client=client)
    assert client.calls  # the check did run...
    fidelity_findings = [
        f for f in report.all_findings if f.law == "Cross-language emotional fidelity"
    ]
    assert fidelity_findings == []  # ...it just found nothing to report.


def test_verify_result_skips_the_check_without_source_language():
    client = FakeFidelityClient({"emotional_fidelity": "flattened", "concern": "x"})
    result_dict = _result_dict_with_source()
    del result_dict["source_language"]
    verify_result(result_dict, client=client)
    assert client.calls == []


def test_verify_result_skips_the_check_when_no_source_sections_present():
    client = FakeFidelityClient({"emotional_fidelity": "flattened", "concern": "x"})
    result_dict = _result_dict_with_source()
    result_dict["source_sections"] = []
    verify_result(result_dict, client=client)
    assert client.calls == []
