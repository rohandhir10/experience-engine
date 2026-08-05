"""Tests for engine/comics_inpaint.py — the inpainting boundary and its
fallback.

No LaMa service and no weights: RemoteInpainter is exercised against
stubbed HTTP responses. What is genuinely tested here is the contract
around the model — mask geometry, the fallback chain, and refusing a
reply that would corrupt the typesetting step — because those are the
parts that must hold whether or not a service is connected.
"""
from __future__ import annotations

import base64
import io

import numpy as np
import pytest
from PIL import Image

from engine import comics_inpaint, comics_redraw
from engine.comics_inpaint import (
    LocalInpainter,
    RemoteInpainter,
    build_mask,
    flatten_to_rgb,
    inpaint_with_fallback,
    mask_is_empty,
)


def _panel(width: int = 120, height: int = 80, color=(200, 180, 160)) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _StubResponse:
    def __init__(self, content=b"", json_body=None, headers=None, status: int = 200):
        self.content = content
        self._json = json_body
        self.headers = headers or {}
        self.status_code = status

    def json(self):
        if self._json is None:
            raise ValueError("not json")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def stub_post(monkeypatch):
    """Replaces httpx.post for RemoteInpainter, capturing what was sent."""
    captured = {}

    def _install(response=None, error=None):
        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            if error:
                raise error
            return response

        monkeypatch.setattr("httpx.post", fake_post)
        return captured

    return _install


# --- flatten_to_rgb: the alpha-compositing fix for the redraw color-fade
# bug report - a naive Image.convert("RGB") drops alpha WITHOUT
# compositing, leaking whatever raw (often garbage) color sat under a
# translucent/transparent pixel through as a visible discoloration. ------


def test_flatten_to_rgb_leaves_an_already_opaque_image_untouched():
    image = Image.new("RGB", (10, 10), (200, 100, 50))
    flattened = flatten_to_rgb(image)
    assert flattened.mode == "RGB"
    assert np.asarray(flattened)[0, 0].tolist() == [200, 100, 50]


def test_flatten_to_rgb_composites_a_fully_transparent_pixel_onto_white():
    rgba = Image.new("RGBA", (10, 10), (0, 0, 0, 0))  # fully transparent, raw color black
    flattened = flatten_to_rgb(rgba)
    assert flattened.mode == "RGB"
    # A naive convert("RGB") would have kept the raw (0, 0, 0) black -
    # compositing onto white must actually change it.
    assert np.asarray(flattened)[0, 0].tolist() == [255, 255, 255]


def test_flatten_to_rgb_correctly_blends_a_translucent_pixel():
    # alpha=128 (~50%) over a black RGB should land roughly halfway to
    # white when composited - nowhere near the raw (10, 10, 10) a naive
    # convert("RGB") would silently keep instead.
    rgba = Image.new("RGBA", (4, 4), (10, 10, 10, 128))
    flattened = flatten_to_rgb(rgba)
    pixel = np.asarray(flattened)[0, 0]
    assert all(120 <= c <= 140 for c in pixel), f"expected ~half-white blend, got {pixel}"


def test_flatten_to_rgb_handles_a_palette_image_with_transparency():
    # "P" mode with a transparency index (classic GIF-style transparency,
    # also legal in PNG) is the other real-world shape this has to catch -
    # `image.mode == "RGBA"` alone would miss it.
    base = Image.new("RGB", (6, 6), (0, 0, 0))
    paletted = base.convert("P", palette=Image.ADAPTIVE)
    paletted.info["transparency"] = 0
    flattened = flatten_to_rgb(paletted)
    assert flattened.mode == "RGB"
    assert np.asarray(flattened)[0, 0].tolist() == [255, 255, 255]


def test_flatten_to_rgb_uses_a_custom_background_when_given_one():
    rgba = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    flattened = flatten_to_rgb(rgba, background=(10, 20, 30))
    assert np.asarray(flattened)[0, 0].tolist() == [10, 20, 30]


# --- mask geometry: the contract both implementations share ---------------


def test_mask_is_white_inside_a_box_and_black_everywhere_else():
    mask = build_mask((100, 50), [(10, 10, 40, 30)])
    array = np.asarray(mask)
    assert array.shape == (50, 100)
    assert array[20, 20] == 255
    assert array[5, 5] == 0
    # The convention LaMa, IOPaint and cv2.inpaint all share.
    assert set(np.unique(array)) <= {0, 255}


def test_overlapping_boxes_become_one_combined_region():
    """Two nearby bubbles must be filled in a single pass - filling them
    one after another means the second reconstructs partly from the
    first's own synthetic pixels rather than from real artwork.
    """
    mask = np.asarray(build_mask((100, 50), [(10, 10, 40, 30), (30, 10, 60, 30)]))
    assert mask[20, 35] == 255
    assert mask[20, 55] == 255


def test_a_zero_area_box_marks_nothing():
    assert mask_is_empty(build_mask((50, 50), [(10, 10, 10, 20)]))
    assert mask_is_empty(build_mask((50, 50), [(20, 10, 10, 30)]))


def test_an_empty_mask_is_detected():
    assert mask_is_empty(build_mask((50, 50), []))
    assert not mask_is_empty(build_mask((50, 50), [(1, 1, 10, 10)]))


def test_redraw_pads_its_mask_beyond_the_measured_box():
    """Text carries a stroke and antialiasing past its bounding box;
    without the margin a halo of the original lettering survives.
    """
    mask = np.asarray(
        comics_redraw.build_region_mask((100, 100), [{"x": 40, "y": 40, "width": 20, "height": 20}])
    )
    pad = comics_inpaint.MASK_PADDING_PX
    assert pad > 0
    assert mask[40 - pad, 40 - pad] == 255
    assert mask[40 - pad - 2, 40 - pad - 2] == 0


def test_redraw_mask_is_clamped_to_the_image_bounds():
    # A box at the very edge must not ask for pixels outside the buffer.
    mask = comics_redraw.build_region_mask(
        (50, 50), [{"x": 0, "y": 0, "width": 50, "height": 50}]
    )
    assert np.asarray(mask).shape == (50, 50)


# --- local inpainting -----------------------------------------------------


def test_local_inpainting_changes_the_masked_pixels():
    panel = _panel()
    panel.paste((0, 0, 0), (20, 20, 60, 50))
    mask = build_mask(panel.size, [(20, 20, 60, 50)])

    result = LocalInpainter().inpaint(panel, mask)

    assert result is not None
    assert np.asarray(result)[35, 40].tolist() != [0, 0, 0]


def test_local_inpainting_leaves_unmasked_pixels_untouched():
    panel = _panel()
    panel.paste((10, 20, 30), (0, 0, 10, 10))
    mask = build_mask(panel.size, [(60, 40, 100, 70)])

    result = LocalInpainter().inpaint(panel, mask)

    assert np.asarray(result)[5, 5].tolist() == [10, 20, 30]


# --- the remote service ---------------------------------------------------


def test_remote_sends_the_panel_and_mask_as_base64_png(stub_post):
    panel = _panel()
    mask = build_mask(panel.size, [(10, 10, 40, 40)])
    captured = stub_post(
        response=_StubResponse(
            content=_png_bytes(_panel()), headers={"content-type": "image/png"}
        )
    )

    RemoteInpainter("http://lama.internal/inpaint").inpaint(panel, mask)

    assert captured["url"] == "http://lama.internal/inpaint"
    sent_mask = Image.open(io.BytesIO(base64.b64decode(captured["json"]["mask"])))
    sent_image = Image.open(io.BytesIO(base64.b64decode(captured["json"]["image"])))
    assert sent_mask.size == panel.size
    assert sent_image.size == panel.size
    # The mask must arrive as a real binary mask, not a colour image.
    assert sent_mask.convert("L").getextrema() == (0, 255)


def test_remote_accepts_raw_image_bytes(stub_post):
    expected = _panel(color=(1, 2, 3))
    stub_post(
        response=_StubResponse(content=_png_bytes(expected), headers={"content-type": "image/png"})
    )
    result = RemoteInpainter("http://x/i").inpaint(_panel(), build_mask((120, 80), [(1, 1, 5, 5)]))
    assert result is not None
    assert np.asarray(result)[0, 0].tolist() == [1, 2, 3]


@pytest.mark.parametrize("key", ["image", "result", "output"])
def test_remote_accepts_a_json_body_carrying_base64(stub_post, key):
    """IOPaint returns raw bytes; thin custom LaMa wrappers commonly
    return JSON. Supporting both avoids dictating the server.
    """
    expected = _panel(color=(9, 8, 7))
    stub_post(
        response=_StubResponse(
            json_body={key: base64.b64encode(_png_bytes(expected)).decode()},
            headers={"content-type": "application/json"},
        )
    )
    result = RemoteInpainter("http://x/i").inpaint(_panel(), build_mask((120, 80), [(1, 1, 5, 5)]))
    assert result is not None
    assert np.asarray(result)[0, 0].tolist() == [9, 8, 7]


def test_remote_rejects_a_reply_of_the_wrong_size(stub_post):
    """A service that resized the panel would silently invalidate every
    bounding box the caller is about to typeset into. Discarding beats
    drawing text at the wrong scale.
    """
    stub_post(
        response=_StubResponse(
            content=_png_bytes(_panel(60, 40)), headers={"content-type": "image/png"}
        )
    )
    assert RemoteInpainter("http://x/i").inpaint(
        _panel(120, 80), build_mask((120, 80), [(1, 1, 5, 5)])
    ) is None


@pytest.mark.parametrize(
    "response",
    [
        _StubResponse(content=b"not an image", headers={"content-type": "image/png"}),
        _StubResponse(json_body={"unexpected": "shape"}, headers={"content-type": "application/json"}),
        _StubResponse(json_body={"image": "!!!not base64!!!"}, headers={"content-type": "application/json"}),
        _StubResponse(content=b"", status=500),
    ],
)
def test_remote_returns_none_for_any_unusable_reply(stub_post, response):
    stub_post(response=response)
    assert RemoteInpainter("http://x/i").inpaint(
        _panel(), build_mask((120, 80), [(1, 1, 5, 5)])
    ) is None


def test_remote_returns_none_when_the_service_is_unreachable(stub_post):
    stub_post(error=RuntimeError("connection refused"))
    assert RemoteInpainter("http://x/i").inpaint(
        _panel(), build_mask((120, 80), [(1, 1, 5, 5)])
    ) is None


# --- the fallback chain: the point of the whole exercise ------------------


def test_a_dead_remote_service_falls_back_to_local_not_to_failure(stub_post):
    """A LaMa service being down must cost redraw QUALITY, never the
    redraw the user actually asked for.
    """
    stub_post(error=RuntimeError("service down"))
    panel = _panel()
    panel.paste((0, 0, 0), (20, 20, 60, 50))
    mask = build_mask(panel.size, [(20, 20, 60, 50)])

    result, method = inpaint_with_fallback(
        panel, mask, inpainter=RemoteInpainter("http://x/i")
    )

    assert method == "local"
    assert np.asarray(result)[35, 40].tolist() != [0, 0, 0]


def test_a_working_remote_service_is_reported_as_remote(stub_post):
    stub_post(
        response=_StubResponse(
            content=_png_bytes(_panel(color=(5, 5, 5))), headers={"content-type": "image/png"}
        )
    )
    _result, method = inpaint_with_fallback(
        _panel(), build_mask((120, 80), [(1, 1, 5, 5)]), inpainter=RemoteInpainter("http://x/i")
    )
    assert method == "remote"


def test_local_is_reported_as_local():
    panel = _panel()
    _result, method = inpaint_with_fallback(
        panel, build_mask(panel.size, [(10, 10, 40, 40)]), inpainter=LocalInpainter()
    )
    assert method == "local"


def test_an_empty_mask_short_circuits_without_calling_anything():
    class _Exploding:
        def inpaint(self, image, mask):
            raise AssertionError("must not be called for an empty mask")

    panel = _panel()
    result, method = inpaint_with_fallback(
        panel, build_mask(panel.size, []), inpainter=_Exploding()
    )
    assert method == "none"
    assert result is panel


def test_everything_failing_returns_the_original_untouched():
    """Honest degradation: the caller then draws over un-erased text,
    which looks wrong but is visible and explicable - unlike a blank or
    half-processed panel.
    """
    class _AlwaysNone:
        def inpaint(self, image, mask):
            return None

    panel = _panel()
    result, method = inpaint_with_fallback(
        panel, build_mask(panel.size, [(10, 10, 40, 40)]), inpainter=_AlwaysNone()
    )
    assert method == "none"
    assert result is panel


# --- configuration --------------------------------------------------------


def test_no_url_configured_builds_the_local_inpainter(monkeypatch):
    from engine import config

    monkeypatch.setattr(config, "INPAINT_URL", "")
    assert isinstance(comics_inpaint.build_inpainter(), LocalInpainter)


def test_a_configured_url_builds_the_remote_inpainter(monkeypatch):
    from engine import config

    monkeypatch.setattr(config, "INPAINT_URL", "http://lama.internal/inpaint")
    assert isinstance(comics_inpaint.build_inpainter(), RemoteInpainter)


# --- end to end through redraw_panel --------------------------------------


def test_redraw_reports_which_inpainter_produced_the_result(monkeypatch):
    monkeypatch.setattr(comics_inpaint, "build_inpainter", lambda: LocalInpainter())
    panel = _panel(200, 120)
    panel.paste((0, 0, 0), (20, 20, 120, 60))

    _png, method = comics_redraw.redraw_panel_detailed(
        _png_bytes(panel),
        [{"bbox": {"x": 20, "y": 20, "width": 100, "height": 40}, "adapted_text": "HELLO"}],
    )
    assert method == "local"


def test_redraw_uses_a_remote_service_when_one_is_configured(monkeypatch, stub_post):
    from engine import config

    monkeypatch.setattr(config, "INPAINT_URL", "http://lama.internal/inpaint")
    panel = _panel(200, 120)
    stub_post(
        response=_StubResponse(
            content=_png_bytes(_panel(200, 120, color=(240, 240, 240))),
            headers={"content-type": "image/png"},
        )
    )

    _png, method = comics_redraw.redraw_panel_detailed(
        _png_bytes(panel),
        [{"bbox": {"x": 20, "y": 20, "width": 100, "height": 40}, "adapted_text": "HELLO"}],
    )
    assert method == "remote"


def test_redraw_still_succeeds_when_the_remote_service_is_down(monkeypatch, stub_post):
    from engine import config

    monkeypatch.setattr(config, "INPAINT_URL", "http://lama.internal/inpaint")
    stub_post(error=RuntimeError("down"))
    panel = _panel(200, 120)
    panel.paste((0, 0, 0), (20, 20, 120, 60))

    png, method = comics_redraw.redraw_panel_detailed(
        _png_bytes(panel),
        [{"bbox": {"x": 20, "y": 20, "width": 100, "height": 40}, "adapted_text": "HELLO"}],
    )
    assert method == "local"
    assert Image.open(io.BytesIO(png)).size == (200, 120)
