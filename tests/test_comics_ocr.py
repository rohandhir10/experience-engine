"""Tests for engine/comics_ocr.py (Google Cloud Vision-backed OCR, via a
service-account credential).

No real network call is made — httpx.post is monkeypatched with a fake
response shaped like Cloud Vision's actual DOCUMENT_TEXT_DETECTION JSON.
Most tests monkeypatch _access_token directly (a fake token string) so
they exercise the request/response parsing without needing a real
service-account key; a separate block of tests exercises _access_token
itself, mocking google.oauth2.service_account.Credentials rather than
performing a real OAuth token exchange.
"""
from __future__ import annotations

import base64
import json
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from engine import comics_ocr
from engine.comics_ocr import (
    OcrError,
    _access_token,
    _bounding_box,
    _block_text,
    _detected_languages,
    extract_text_regions,
    sort_reading_order,
)


@pytest.fixture(autouse=True)
def _clear_token_cache():
    """_access_token caches across calls, keyed by a hash of the
    credential env var. Two tests using the same fake credential would
    otherwise share a cached token, so the second one would silently
    assert against the first one's result instead of its own.
    """
    comics_ocr._reset_token_cache()
    yield
    comics_ocr._reset_token_cache()


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text or str(json_body)

    def json(self) -> dict:
        return self._json_body


def _vision_success_response(
    blocks: list[dict],
    width: int = 500,
    height: int = 600,
    detected_languages: list[dict] | None = None,
) -> dict:
    page: dict = {"width": width, "height": height, "blocks": blocks}
    if detected_languages is not None:
        page["property"] = {"detectedLanguages": detected_languages}
    return {"responses": [{"fullTextAnnotation": {"pages": [page]}}]}


def _block(text_words: list[str], vertices: list[dict], confidence: float) -> dict:
    return {
        "boundingBox": {"vertices": vertices},
        "confidence": confidence,
        "paragraphs": [
            {
                "words": [
                    {"symbols": [{"text": ch} for ch in word]} for word in text_words
                ]
            }
        ],
    }


@pytest.fixture(autouse=True)
def _fake_token(monkeypatch):
    """Every test below _access_token's own block cares about request/
    response handling, not authentication - stub it out with a fake
    token so those tests don't need a real service-account key.
    """
    monkeypatch.setattr(comics_ocr, "_access_token", lambda: "fake-token")


def test_block_text_joins_words_with_spaces_and_paragraphs_with_newlines():
    block = {
        "paragraphs": [
            {"words": [{"symbols": [{"text": "H"}, {"text": "i"}]}]},
            {"words": [{"symbols": [{"text": "b"}, {"text": "ye"}]}]},
        ]
    }
    assert _block_text(block) == "Hi\nbye"


def test_block_text_skips_empty_paragraphs():
    block = {"paragraphs": [{"words": []}, {"words": [{"symbols": [{"text": "ok"}]}]}]}
    assert _block_text(block) == "ok"


def test_bounding_box_collapses_quadrilateral_to_axis_aligned_rect():
    vertices = [{"x": 10, "y": 10}, {"x": 90, "y": 12}, {"x": 88, "y": 40}, {"x": 12, "y": 38}]
    box = _bounding_box(vertices)
    assert box == {"x": 10, "y": 10, "width": 80, "height": 30}


def test_bounding_box_handles_missing_vertices():
    assert _bounding_box([]) == {"x": 0, "y": 0, "width": 0, "height": 0}


def _region(text: str, x: int, y: int, width: int = 50, height: int = 20) -> dict:
    return {"text": text, "bbox": {"x": x, "y": y, "width": width, "height": height}}


def test_sort_reading_order_empty_list():
    assert sort_reading_order([]) == []


def test_sort_reading_order_single_region_unchanged():
    regions = [_region("only", 10, 10)]
    assert sort_reading_order(regions) == regions


def test_sort_reading_order_orders_separate_rows_top_to_bottom():
    # No vertical overlap at all - "bottom" is far below "top" even
    # though it's positioned further LEFT, which a naive left-to-right-
    # only sort would get wrong.
    top = _region("top", x=200, y=0)
    bottom = _region("bottom", x=0, y=500)
    ordered = sort_reading_order([bottom, top])
    assert [r["text"] for r in ordered] == ["top", "bottom"]


def test_sort_reading_order_same_row_left_to_right_by_default():
    left = _region("left", x=0, y=0)
    right = _region("right", x=200, y=5)  # overlapping y-range = same row
    ordered = sort_reading_order([right, left])
    assert [r["text"] for r in ordered] == ["left", "right"]


def test_sort_reading_order_same_row_right_to_left_for_japanese():
    left = _region("left", x=0, y=0)
    right = _region("right", x=200, y=5)
    ordered = sort_reading_order([left, right], language="Japanese")
    assert [r["text"] for r in ordered] == ["right", "left"]


def test_sort_reading_order_only_japanese_triggers_right_to_left():
    left = _region("left", x=0, y=0)
    right = _region("right", x=200, y=5)
    for language in ["Korean", "English", "Hindi", "Spanish", "Urdu", None]:
        ordered = sort_reading_order([left, right], language=language)
        assert [r["text"] for r in ordered] == ["left", "right"], language


def test_sort_reading_order_three_regions_two_rows():
    # A row of two (left-to-right), then a separate row below.
    top_left = _region("top_left", x=0, y=0)
    top_right = _region("top_right", x=200, y=5)
    bottom = _region("bottom", x=0, y=400)
    ordered = sort_reading_order([bottom, top_right, top_left])
    assert [r["text"] for r in ordered] == ["top_left", "top_right", "bottom"]


def test_sort_reading_order_below_overlap_threshold_becomes_separate_rows():
    # Two regions whose y-ranges overlap only slightly (well under the
    # 0.5 threshold of the shorter region's height) must NOT merge into
    # one row - each is its own row, ordered by vertical position.
    a = _region("a", x=200, y=0, height=20)  # spans y=0..20
    b = _region("b", x=0, y=18, height=20)  # spans y=18..38, overlap=2/20=0.1
    ordered = sort_reading_order([b, a])
    assert [r["text"] for r in ordered] == ["a", "b"]


def test_sort_reading_order_at_or_above_threshold_merges_into_one_row():
    # Overlap of 10/20 = 0.5, exactly at the threshold - same row, so x
    # order (right region first, since b is further right) applies.
    a = _region("a", x=0, y=0, height=20)  # spans y=0..20
    b = _region("b", x=200, y=10, height=20)  # spans y=10..30, overlap=10/20=0.5
    ordered = sort_reading_order([a, b])
    assert [r["text"] for r in ordered] == ["a", "b"]


def test_sort_reading_order_is_stable_for_already_ordered_input():
    regions = [_region("one", 0, 0), _region("two", 100, 0), _region("three", 200, 0)]
    assert [r["text"] for r in sort_reading_order(regions)] == ["one", "two", "three"]


def test_extracts_real_looking_blocks_with_scaled_confidence(monkeypatch):
    blocks = [
        _block(
            ["HELLO", "THERE"],
            [{"x": 10, "y": 10}, {"x": 110, "y": 10}, {"x": 110, "y": 30}, {"x": 10, "y": 30}],
            0.95,
        ),
        _block(
            ["GOODBYE"],
            [{"x": 10, "y": 100}, {"x": 130, "y": 100}, {"x": 130, "y": 120}, {"x": 10, "y": 120}],
            0.9,
        ),
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, _vision_success_response(blocks)),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["image_width"] == 500
    assert result["image_height"] == 600
    assert len(result["regions"]) == 2
    assert result["regions"][0]["text"] == "HELLO THERE"
    assert result["regions"][0]["confidence"] == 95.0
    assert result["regions"][0]["bbox"] == {"x": 10, "y": 10, "width": 100, "height": 20}
    assert "HELLO THERE" in result["full_text"]
    assert result["warning"] is None


def test_extract_text_regions_orders_a_japanese_row_right_to_left(monkeypatch):
    # Two blocks in the same row (overlapping y-range), "LEFT" drawn on
    # the left of the panel and "RIGHT" on the right - Vision itself
    # returns them in an arbitrary order (left block first here), and
    # only sort_reading_order should be responsible for correcting it.
    blocks = [
        _block(
            ["LEFT"],
            [{"x": 10, "y": 10}, {"x": 60, "y": 10}, {"x": 60, "y": 30}, {"x": 10, "y": 30}],
            0.9,
        ),
        _block(
            ["RIGHT"],
            [{"x": 300, "y": 12}, {"x": 350, "y": 12}, {"x": 350, "y": 32}, {"x": 300, "y": 32}],
            0.9,
        ),
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, _vision_success_response(blocks)),
    )
    result = extract_text_regions(b"fake-image-bytes", language="Japanese")
    assert [r["text"] for r in result["regions"]] == ["RIGHT", "LEFT"]
    assert result["full_text"].index("RIGHT") < result["full_text"].index("LEFT")


def test_extract_text_regions_keeps_left_to_right_for_non_japanese(monkeypatch):
    blocks = [
        _block(
            ["LEFT"],
            [{"x": 10, "y": 10}, {"x": 60, "y": 10}, {"x": 60, "y": 30}, {"x": 10, "y": 30}],
            0.9,
        ),
        _block(
            ["RIGHT"],
            [{"x": 300, "y": 12}, {"x": 350, "y": 12}, {"x": 350, "y": 32}, {"x": 300, "y": 32}],
            0.9,
        ),
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, _vision_success_response(blocks)),
    )
    result = extract_text_regions(b"fake-image-bytes", language="Korean")
    assert [r["text"] for r in result["regions"]] == ["LEFT", "RIGHT"]


def test_request_is_authenticated_with_a_bearer_token(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["headers"] = headers
        return _FakeResponse(200, {"responses": [{}]})

    monkeypatch.setattr(comics_ocr.httpx, "post", fake_post)
    extract_text_regions(b"fake-image-bytes")
    assert captured["headers"] == {"Authorization": "Bearer fake-token"}


def test_majority_low_confidence_blocks_produce_a_warning(monkeypatch):
    blocks = [
        _block(["a"], [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}], 0.3),
        _block(["b"], [{"x": 0, "y": 20}, {"x": 10, "y": 20}, {"x": 10, "y": 30}, {"x": 0, "y": 30}], 0.4),
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, _vision_success_response(blocks)),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["warning"] is not None
    assert "low" in result["warning"].lower()


def test_no_text_detected_returns_empty_regions_and_a_warning(monkeypatch):
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, {"responses": [{}]}),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["regions"] == []
    assert result["warning"] == "No text detected in this panel. Type it in by hand."
    assert result["detected_languages"] == []


def test_detected_languages_are_surfaced_most_confident_first(monkeypatch):
    blocks = [
        _block(["a"], [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}], 0.9)
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(
            200,
            _vision_success_response(
                blocks,
                detected_languages=[
                    {"languageCode": "en", "confidence": 0.1},
                    {"languageCode": "ko", "confidence": 0.92},
                ],
            ),
        ),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["detected_languages"] == [
        {"language_code": "ko", "language_name": "Korean", "confidence": 92.0},
        {"language_code": "en", "language_name": "English", "confidence": 10.0},
    ]


def test_unrecognized_detected_language_reports_raw_code_with_no_name(monkeypatch):
    blocks = [
        _block(["a"], [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}], 0.9)
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(
            200,
            _vision_success_response(
                blocks, detected_languages=[{"languageCode": "th", "confidence": 0.8}]
            ),
        ),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["detected_languages"] == [
        {"language_code": "th", "language_name": None, "confidence": 80.0}
    ]


def test_detected_languages_function_ignores_entries_with_no_language_code():
    page = {"property": {"detectedLanguages": [{"confidence": 0.9}, {"languageCode": "ja", "confidence": 0.5}]}}
    assert _detected_languages(page) == [
        {"language_code": "ja", "language_name": "Japanese", "confidence": 50.0}
    ]


def test_detected_languages_function_handles_missing_property():
    assert _detected_languages({}) == []


def test_http_error_status_raises_ocr_error(monkeypatch):
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(403, {}, text="Forbidden"),
    )
    with pytest.raises(OcrError, match="403"):
        extract_text_regions(b"fake-image-bytes")


def test_vision_error_in_response_raises_ocr_error(monkeypatch):
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(
            200, {"responses": [{"error": {"message": "Bad image data."}}]}
        ),
    )
    with pytest.raises(OcrError, match="Bad image data"):
        extract_text_regions(b"fake-image-bytes")


def test_known_language_is_sent_as_a_hint(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(200, {"responses": [{}]})

    monkeypatch.setattr(comics_ocr.httpx, "post", fake_post)
    extract_text_regions(b"fake-image-bytes", language="Korean")
    assert captured["payload"]["requests"][0]["imageContext"]["languageHints"] == ["ko"]


def test_unknown_or_missing_language_sends_no_hint(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(200, {"responses": [{}]})

    monkeypatch.setattr(comics_ocr.httpx, "post", fake_post)
    extract_text_regions(b"fake-image-bytes", language="French")
    assert "imageContext" not in captured["payload"]["requests"][0]

    extract_text_regions(b"fake-image-bytes")
    assert "imageContext" not in captured["payload"]["requests"][0]


# ---------------------------------------------------------------------------
# _access_token itself — the fixture above stubs this out for every test
# above this point, so these are the only tests that exercise the real
# credential-loading/decoding logic (mocking google-auth's Credentials
# class rather than performing a real OAuth exchange, which needs an
# actual private key to sign a JWT).
# ---------------------------------------------------------------------------


def _encoded(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


def test_missing_credentials_env_var_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", raising=False)
    with pytest.raises(OcrError, match="GOOGLE_CLOUD_VISION_CREDENTIALS_JSON"):
        _access_token()


def test_non_base64_value_raises_a_clear_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", "not-valid-base64!!!")
    with pytest.raises(OcrError, match="not valid base64-encoded JSON"):
        _access_token()


def test_base64_of_non_json_raises_a_clear_error(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON",
        base64.b64encode(b"this is not json").decode(),
    )
    with pytest.raises(OcrError, match="not valid base64-encoded JSON"):
        _access_token()


def test_invalid_service_account_structure_raises_a_clear_error(monkeypatch):
    # Valid base64 + valid JSON, but missing the fields a real
    # service-account key needs (private_key, client_email, token_uri).
    monkeypatch.setenv("GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "service_account"}))
    with pytest.raises(OcrError, match="Could not authenticate"):
        _access_token()


def test_valid_credentials_return_the_refreshed_token(monkeypatch):
    class _FakeCredentials:
        def __init__(self, *a, **k):
            self.token = None

        def refresh(self, request):
            self.token = "real-token"

    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "service_account"})
    )
    monkeypatch.setattr(
        comics_ocr.service_account.Credentials,
        "from_service_account_info",
        lambda info, scopes=None: _FakeCredentials(),
    )
    assert _access_token() == "real-token"


# ---------------------------------------------------------------------------
# Token caching — the whole point is that a second call does NOT perform
# another OAuth exchange, so every test here counts real refresh() calls.
# ---------------------------------------------------------------------------


class _CountingCredentials:
    """Stands in for a real service-account Credentials object, counting
    how many times a token exchange actually happened.
    """

    instances: list["_CountingCredentials"] = []

    def __init__(self, expiry=None):
        self.token = None
        self.expiry = expiry
        self.refresh_calls = 0
        _CountingCredentials.instances.append(self)

    def refresh(self, request):
        self.refresh_calls += 1
        self.token = f"token-{len(_CountingCredentials.instances)}"


@pytest.fixture
def counting_credentials(monkeypatch):
    _CountingCredentials.instances = []
    expiry_holder = {"expiry": None}

    monkeypatch.setattr(
        comics_ocr.service_account.Credentials,
        "from_service_account_info",
        lambda info, scopes=None: _CountingCredentials(expiry_holder["expiry"]),
    )
    return expiry_holder


def _total_refreshes() -> int:
    return sum(c.refresh_calls for c in _CountingCredentials.instances)


def test_second_call_reuses_the_cached_token_without_a_new_exchange(
    monkeypatch, counting_credentials
):
    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "service_account"})
    )
    first = _access_token()
    second = _access_token()

    assert first == second
    assert _total_refreshes() == 1


def test_rotating_the_credential_invalidates_the_cache(monkeypatch, counting_credentials):
    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "service_account"})
    )
    first = _access_token()

    # A genuinely different credential must never be served the token
    # minted from the previous one.
    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON",
        _encoded({"type": "service_account", "client_email": "rotated@example.com"}),
    )
    second = _access_token()

    assert first != second
    assert _total_refreshes() == 2


def test_a_token_near_expiry_is_refreshed_rather_than_served(
    monkeypatch, counting_credentials
):
    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "service_account"})
    )
    _access_token()
    assert _total_refreshes() == 1

    # Rewrite the cache so the stored token sits inside the safety margin.
    fingerprint, token, _ = comics_ocr._token_cache
    comics_ocr._token_cache = (
        fingerprint,
        token,
        time.time() + comics_ocr._TOKEN_EXPIRY_MARGIN_SECONDS - 1,
    )

    _access_token()
    assert _total_refreshes() == 2


def test_a_naive_expiry_is_read_as_utc_not_local_time(counting_credentials):
    # google-auth reports expiry as a naive datetime already in UTC.
    # Reading it as local time would place expiry hours off in either
    # direction, so a token would be cached far too long or thrown away
    # immediately - depending purely on the server's timezone.
    naive_utc = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    credentials = _CountingCredentials(expiry=naive_utc)

    expiry = comics_ocr._token_expiry_epoch(credentials)

    assert abs(expiry - (time.time() + 3600)) < 60


def test_credentials_without_an_expiry_fall_back_to_a_conservative_ttl(
    counting_credentials,
):
    expiry = comics_ocr._token_expiry_epoch(_CountingCredentials(expiry=None))
    expected = time.time() + comics_ocr._DEFAULT_TOKEN_TTL_SECONDS
    assert abs(expiry - expected) < 60
    # Must stay comfortably inside Google's real one-hour token lifetime.
    assert comics_ocr._DEFAULT_TOKEN_TTL_SECONDS < 3600


def test_a_failed_exchange_caches_nothing(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "x"}))

    def _boom(info, scopes=None):
        raise ValueError("bad key")

    monkeypatch.setattr(
        comics_ocr.service_account.Credentials, "from_service_account_info", _boom
    )
    with pytest.raises(OcrError):
        _access_token()
    assert comics_ocr._token_cache is None


def test_concurrent_cold_calls_perform_exactly_one_exchange(
    monkeypatch, counting_credentials
):
    """The thundering-herd case the lock exists for: N threads arriving on
    a cold cache must produce one token exchange, not N.
    """
    monkeypatch.setenv(
        "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON", _encoded({"type": "service_account"})
    )
    tokens: list[str] = []
    barrier = threading.Barrier(8)

    def _worker():
        barrier.wait()
        tokens.append(_access_token())

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(tokens)) == 1
    assert _total_refreshes() == 1


# ---------------------------------------------------------------------------
# detectedBreak-aware reconstruction.
#
# Reproduces a real production failure on a Korean webtoon panel. Vision
# segments Korean at a sub-word level, handing back each particle (조사) as
# its own "word". The old space-joining reconstruction turned
#
#     공주님을 / 막지 못하고 / 전하께 보인다면 / 저희가 매를 / 맞을 겁니다.
#
# into
#
#     공주님 을 막지 못하고 / 전하 께 보인다 면 / 저희 가 매 를 / 맞을 겁니다
#
# - a space before every particle, which is a grammatical error in Korean.
# The engine then received broken Korean as its source text, so the
# corruption was upstream of every translation decision made from it.
# ---------------------------------------------------------------------------


def _sym(char: str, break_type: str | None = None) -> dict:
    symbol: dict = {"text": char}
    if break_type:
        symbol["property"] = {"detectedBreak": {"type": break_type}}
    return symbol


def _word(text: str, break_type: str | None = None) -> dict:
    """One Vision "word", with an optional break after its last symbol."""
    symbols = [_sym(c) for c in text[:-1]] + [_sym(text[-1], break_type)]
    return {"symbols": symbols}


def _para(*words: dict) -> dict:
    return {"paragraphs": [{"words": list(words)}]}


def test_korean_particles_attach_with_no_space():
    """The actual bug: a particle carries no break, so nothing may be
    inserted before it.

    The trailing LINE_BREAK is not incidental - a real
    DOCUMENT_TEXT_DETECTION response always marks the end of a line, and
    without any break at all in the block the fallback below correctly
    kicks in instead. An earlier version of this test omitted it and so
    was testing the fallback while claiming to test this.
    """
    block = _para(_word("공주님"), _word("을", "LINE_BREAK"))
    assert _block_text(block) == "공주님을"


def test_a_real_space_between_words_is_preserved():
    block = _para(_word("막지", "SPACE"), _word("못하고"))
    assert _block_text(block) == "막지 못하고"


def test_the_full_production_bubble_round_trips_exactly():
    block = _para(
        _word("공주님"), _word("을", "LINE_BREAK"),
        _word("막지", "SPACE"), _word("못하고", "LINE_BREAK"),
        _word("전하"), _word("께", "SPACE"), _word("보인다"), _word("면", "LINE_BREAK"),
        _word("저희"), _word("가", "SPACE"), _word("매"), _word("를", "LINE_BREAK"),
        _word("맞을", "SPACE"), _word("겁니다."),
    )
    assert _block_text(block) == (
        "공주님을\n막지 못하고\n전하께 보인다면\n저희가 매를\n맞을 겁니다."
    )


def test_no_spurious_space_appears_anywhere_in_a_korean_read():
    """Guards the specific regression: not one of the particles that were
    split off may come back with a space in front of it."""
    block = _para(
        _word("공주님"), _word("을", "LINE_BREAK"),
        _word("전하"), _word("께", "SPACE"), _word("보인다"), _word("면"),
    )
    text = _block_text(block)
    for broken in ("공주님 을", "전하 께", "보인다 면"):
        assert broken not in text


def test_english_words_still_get_their_spaces():
    block = _para(_word("HOLD", "SPACE"), _word("ON", "SPACE"), _word("TIGHT"))
    assert _block_text(block) == "HOLD ON TIGHT"


@pytest.mark.parametrize("break_type", ["LINE_BREAK", "EOL_SURE_SPACE"])
def test_line_breaks_become_newlines(break_type):
    block = _para(_word("FIRST", break_type), _word("SECOND"))
    assert _block_text(block) == "FIRST\nSECOND"


def test_sure_space_is_treated_as_a_space():
    block = _para(_word("A", "SURE_SPACE"), _word("B"))
    assert _block_text(block) == "A B"


def test_a_hyphenated_word_is_rejoined_rather_than_split():
    block = _para(_word("some", "HYPHEN"), _word("thing"))
    assert _block_text(block) == "something"


def test_a_block_with_no_break_information_falls_back_to_spaces():
    """Some responses omit detectedBreak entirely. Concatenating with
    nothing would run English words together - a worse failure than the
    one being fixed - so the old behaviour is the fallback."""
    block = _para(_word("HELLO"), _word("THERE"))
    assert _block_text(block) == "HELLO THERE"


def test_multiple_paragraphs_are_separated_without_blank_lines():
    block = {
        "paragraphs": [
            {"words": [_word("ONE", "LINE_BREAK")]},
            {"words": [_word("TWO")]},
        ]
    }
    assert _block_text(block) == "ONE\nTWO"


def test_trailing_break_is_not_kept_as_content():
    block = _para(_word("DONE", "LINE_BREAK"))
    assert _block_text(block) == "DONE"


def test_an_unrecognised_break_type_inserts_nothing():
    # Better to under-separate than to invent whitespace the API didn't
    # actually report.
    block = _para(_word("A", "SOMETHING_NEW"), _word("B"))
    assert _block_text(block) == "AB"
