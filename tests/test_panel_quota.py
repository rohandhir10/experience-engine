"""Tests for the per-IP ceiling on the two per-panel comics endpoints
(/api/comics/ocr, /api/comics/redraw).

Both endpoints previously had no ceiling of any kind: every OCR call is a
real metered Google Cloud Vision request and every redraw is real
inpainting work, both billed per call, and a plain loop against either
could run up an unbounded bill. They also can't share the adaptation
quota's numbers - that cap is 3/day, while ONE legitimate chapter fires
one call per panel - hence the separate scope and the much larger limits.
"""
from __future__ import annotations

import io
from collections import defaultdict

import pytest
from fastapi import HTTPException

import server.main as main
from server import quota


class _FakeRequest:
    """Only what _client_ip reads."""

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}
        self.client = None


@pytest.fixture(autouse=True)
def _reset_quota_state(monkeypatch):
    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    monkeypatch.setattr(quota, "_memory_monthly_counts", defaultdict(int))
    monkeypatch.delenv("DATABASE_URL", raising=False)


# --- The bucket-key namespacing the two scopes depend on --------------


def test_panel_scope_and_adaptation_scope_are_independent_counters():
    """The whole point of the scope: OCR-ing a chapter must not consume
    the (much smaller) allowance for actually adapting one."""
    assert quota.check_and_increment("1.2.3.4", 1, scope="panel") is True
    # Panel bucket is now full, but the default (adaptation) bucket is
    # untouched for the same IP.
    assert quota.check_and_increment("1.2.3.4", 1, scope="panel") is False
    assert quota.check_and_increment("1.2.3.4", 1) is True


def test_default_scope_key_is_byte_identical_to_the_unscoped_key():
    """Pre-existing stored rows are keyed by the bare IP - an empty scope
    has to keep hitting exactly those, or every existing counter silently
    resets the moment this ships."""
    assert quota._bucket_key("1.2.3.4", "") == "1.2.3.4"
    assert quota._bucket_key("1.2.3.4", "panel") == "panel:1.2.3.4"


def test_different_ips_stay_independent_within_the_panel_scope():
    assert quota.check_and_increment("1.2.3.4", 1, scope="panel") is True
    assert quota.check_and_increment("5.6.7.8", 1, scope="panel") is True
    assert quota.check_and_increment("1.2.3.4", 1, scope="panel") is False


def test_monthly_scope_is_also_independent():
    assert quota.check_and_increment_monthly("1.2.3.4", 1, scope="panel") is True
    assert quota.check_and_increment_monthly("1.2.3.4", 1, scope="panel") is False
    assert quota.check_and_increment_monthly("1.2.3.4", 1) is True


# --- _check_panel_quota itself ----------------------------------------


def test_allows_up_to_the_daily_limit_then_raises_429(monkeypatch):
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 2)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)

    main._check_panel_quota("1.2.3.4", "reading panels")
    main._check_panel_quota("1.2.3.4", "reading panels")
    with pytest.raises(HTTPException) as exc:
        main._check_panel_quota("1.2.3.4", "reading panels")
    assert exc.value.status_code == 429
    assert "reading panels" in exc.value.detail


def test_monthly_limit_is_enforced_independently_of_the_daily_one(monkeypatch):
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 0)  # disabled
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 1)

    main._check_panel_quota("1.2.3.4", "redrawing panels")
    with pytest.raises(HTTPException) as exc:
        main._check_panel_quota("1.2.3.4", "redrawing panels")
    assert exc.value.status_code == 429
    assert "month" in exc.value.detail.lower()


def test_zero_limits_disable_the_ceiling_entirely(monkeypatch):
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 0)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)
    for _ in range(50):
        main._check_panel_quota("1.2.3.4", "reading panels")


def test_panel_quota_does_not_consume_the_adaptation_allowance(monkeypatch):
    """Falsification of the real risk this design exists to avoid: a
    normal chapter's worth of OCR must leave the user's ability to
    actually adapt a chapter completely untouched."""
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 100)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)
    monkeypatch.setattr(main, "DAILY_LIMIT", 3)
    monkeypatch.setattr(main, "MONTHLY_LIMIT", 6)

    for _ in range(60):
        main._check_panel_quota("1.2.3.4", "reading panels")

    # Still has the full adaptation allowance.
    main._check_quota("1.2.3.4")
    main._check_quota("1.2.3.4")
    main._check_quota("1.2.3.4")
    with pytest.raises(HTTPException):
        main._check_quota("1.2.3.4")


def test_defaults_are_large_enough_for_one_max_size_chapter():
    """A MAX_COMICS_PANELS chapter costs at most one OCR + one redraw per
    panel. If the shipped default couldn't absorb that, the cap would
    break normal use rather than bound abuse - which is exactly the
    failure mode that keeps the cap from being added at all."""
    worst_case_calls_for_one_chapter = main.MAX_COMICS_PANELS * 2
    assert main.PANEL_DAILY_LIMIT >= worst_case_calls_for_one_chapter
    assert main.PANEL_MONTHLY_LIMIT >= main.PANEL_DAILY_LIMIT


# --- Wired into the real endpoints ------------------------------------


def _stub_vision(monkeypatch):
    """Keep these tests on the quota logic, not on Cloud Vision - there
    are no real credentials here, and the endpoint's read path is already
    covered in tests/test_server.py."""
    monkeypatch.setattr(
        main.comics_ocr,
        "extract_text_regions",
        lambda image_bytes, language=None: {
            "regions": [], "full_text": "", "warning": None, "detected_languages": [],
        },
    )


class _FakeUploadFile:
    """Same shape tests/test_server.py's equivalent uses - `.file.read()`
    plus the `.content_type` the endpoint hands to the vision reader."""

    def __init__(self, content: bytes, content_type: str = "image/png") -> None:
        self.file = io.BytesIO(content)
        self.content_type = content_type


def test_ocr_endpoint_enforces_the_panel_quota(monkeypatch):
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)
    _stub_vision(monkeypatch)

    main.comics_ocr_endpoint(_FakeRequest(), image=_FakeUploadFile(b"bytes"), language=None)
    with pytest.raises(HTTPException) as exc:
        main.comics_ocr_endpoint(_FakeRequest(), image=_FakeUploadFile(b"bytes"), language=None)
    assert exc.value.status_code == 429


def test_an_oversized_upload_is_rejected_without_spending_quota(monkeypatch):
    """The size check runs first deliberately: a rejected upload never
    reaches Vision, so it costs nothing and must not spend an allowance
    the caller could have used on a real panel."""
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)
    monkeypatch.setattr(main, "MAX_IMAGE_BYTES", 10)
    _stub_vision(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        main.comics_ocr_endpoint(
            _FakeRequest(), image=_FakeUploadFile(b"x" * 100), language=None
        )
    assert exc.value.status_code == 413

    # The real panel that follows still gets its full allowance.
    monkeypatch.setattr(main, "MAX_IMAGE_BYTES", 15 * 1024 * 1024)
    main.comics_ocr_endpoint(_FakeRequest(), image=_FakeUploadFile(b"bytes"), language=None)


def test_two_visitors_get_their_own_panel_allowances(monkeypatch):
    """Depends on the forwarded-client-IP fix (tests/test_client_ip.py):
    without it both of these would bucket under the same peer address and
    the second visitor would be refused on the first one's usage."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)
    _stub_vision(monkeypatch)

    def visitor(ip: str) -> _FakeRequest:
        return _FakeRequest(
            {"x-castia-internal-secret": "test-secret", "x-castia-client-ip": ip}
        )

    main.comics_ocr_endpoint(visitor("203.0.113.7"), image=_FakeUploadFile(b"a"), language=None)
    # A different visitor is unaffected by the first one having used theirs.
    main.comics_ocr_endpoint(visitor("198.51.100.42"), image=_FakeUploadFile(b"a"), language=None)
    # But the first visitor really is capped.
    with pytest.raises(HTTPException) as exc:
        main.comics_ocr_endpoint(
            visitor("203.0.113.7"), image=_FakeUploadFile(b"a"), language=None
        )
    assert exc.value.status_code == 429


# --- Redraw: the cache-hit interaction --------------------------------


def _real_png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (120, 60), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_redraw_endpoint_enforces_the_panel_quota(monkeypatch, tmp_path):
    monkeypatch.setattr(main.cache, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)

    image_bytes = _real_png_bytes()

    def regions_for(text: str) -> str:
        import json

        return json.dumps(
            [{"bbox": {"x": 5, "y": 5, "width": 50, "height": 20}, "adapted_text": text}]
        )

    main.comics_redraw_endpoint(
        _FakeRequest(), image=_FakeUploadFile(image_bytes), regions=regions_for("one"),
        default_font=None,
    )
    # A DIFFERENT request (different text -> different content id), so
    # this is a real second redraw, not a cache hit.
    with pytest.raises(HTTPException) as exc:
        main.comics_redraw_endpoint(
            _FakeRequest(), image=_FakeUploadFile(image_bytes), regions=regions_for("two"),
            default_font=None,
        )
    assert exc.value.status_code == 429


def test_a_cache_hit_does_not_spend_panel_quota(monkeypatch, tmp_path):
    """This module's stated convention (server/main.py's docstring) is
    that cache hits don't count against any quota - a page reload or a
    second browser tab on the same panel runs no inpainting and costs
    nothing, so it must not consume the allowance."""
    import json

    monkeypatch.setattr(main.cache, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)

    image_bytes = _real_png_bytes()
    regions = json.dumps(
        [{"bbox": {"x": 5, "y": 5, "width": 50, "height": 20}, "adapted_text": "hello"}]
    )

    first = main.comics_redraw_endpoint(
        _FakeRequest(), image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
    )
    # Identical request: served from cache, so it must NOT raise despite
    # the allowance already being fully spent by the first call.
    for _ in range(5):
        again = main.comics_redraw_endpoint(
            _FakeRequest(), image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
        )
        assert again["id"] == first["id"]


def test_a_rejected_bad_request_does_not_spend_panel_quota(monkeypatch, tmp_path):
    """Validation failures run no inpainting either - a caller fixing a
    typo in a font name shouldn't lose an allowance over it."""
    monkeypatch.setattr(main.cache, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(main, "PANEL_DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "PANEL_MONTHLY_LIMIT", 0)

    import json

    image_bytes = _real_png_bytes()
    good_regions = json.dumps(
        [{"bbox": {"x": 5, "y": 5, "width": 50, "height": 20}, "adapted_text": "hello"}]
    )

    with pytest.raises(HTTPException) as exc:
        main.comics_redraw_endpoint(
            _FakeRequest(), image=_FakeUploadFile(image_bytes), regions=good_regions,
            default_font="not-a-real-font",
        )
    assert exc.value.status_code == 400

    # The allowance survived the rejected request.
    main.comics_redraw_endpoint(
        _FakeRequest(), image=_FakeUploadFile(image_bytes), regions=good_regions, default_font=None
    )
