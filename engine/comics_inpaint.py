"""Background reconstruction behind erased comic text.

Same microservice shape as engine/comics_recognize.py, for the same
reason: the good model is a torch model with downloaded weights, and
this project's API image is python:3.11-slim. LaMa runs in its own
service; the API container stays small and keeps working without it.

    Inpainter (Protocol)
      |- LocalInpainter   OpenCV Telea. Always available, no weights,
      |                   no network. The fallback and the dev default.
      `- RemoteInpainter  A LaMa/IOPaint service over HTTP.

WHAT THE UPGRADE IS ACTUALLY FOR
--------------------------------
OpenCV's Telea algorithm fills a hole by diffusing surrounding pixel
colour inward. On a flat white speech bubble that is genuinely
indistinguishable from a correct result, which is why it was worth
shipping first. On text sitting over drawn artwork - screentone, hair,
a background crowd - it smears, because it has no notion of what the
artwork *is*, only of what colour borders the hole. LaMa is a learned
model that reconstructs plausible structure, which is the difference
between erasing text from a bubble and erasing it from a drawing.

MASK CONTRACT
-------------
Both implementations take the same mask: an 8-bit greyscale image the
size of the panel, 255 where pixels must be reconstructed and 0 where
the original must be left untouched. That convention is LaMa's and
IOPaint's, and it is also what cv2.inpaint expects, so one mask serves
both and neither implementation has to know which one built it.

Failure returns None rather than raising, and the caller falls back to
local inpainting. A remote service being down must degrade redraw
quality, never fail a redraw the user asked for.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Protocol

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def flatten_to_rgb(image: Image.Image, background: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """The one correct way to strip transparency from a panel before any
    pixel work happens - `Image.convert("RGB")` on its own does NOT
    composite onto a background; it just drops the alpha channel and
    keeps whatever RGB values sat underneath it, which are frequently
    garbage for a translucent or fully-transparent pixel (many encoders
    don't bother writing a sensible color under alpha=0). A panel with a
    real alpha channel - a ZIP-slice PNG, a PDF page rendered to an RGBA
    canvas (web/lib/pdfToImages.ts) - can then look subtly discolored or
    faded everywhere that raw, uncomposited color leaks through, most
    visibly at antialiased edges.

    Composites onto a plain white background (comic pages are
    overwhelmingly on white/near-white paper) whenever the image actually
    carries transparency (RGBA, LA, or a palette image with a
    "transparency" entry); every other mode is untouched by this and
    falls through to the same plain convert("RGB") as before, since
    there's no alpha to have lost information in the first place.
    """
    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if not has_alpha:
        return image.convert("RGB")

    rgba = image.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, background)
    flattened.paste(rgba, mask=rgba.split()[-1])
    return flattened

# Grow every mask box by this many pixels. Text almost always carries a
# stroke, an outline, or antialiasing a pixel or two beyond its measured
# bounding box; without the margin, a faint halo of the original
# lettering survives the fill and is clearly visible against the
# reconstruction.
MASK_PADDING_PX = 4


class Inpainter(Protocol):
    """Reconstructs the masked areas of an image.

    Returns the full image with those areas filled, or None if it
    could not - never a partially-processed image, since the caller
    cannot tell the difference and would ship it.
    """

    def inpaint(self, image: Image.Image, mask: Image.Image) -> Image.Image | None:
        ...


def build_mask(size: tuple[int, int], boxes: list[tuple[int, int, int, int]]) -> Image.Image:
    """One 8-bit mask covering every region, white where the artwork must
    be rebuilt.

    Built as a single combined mask rather than one per region on
    purpose: two nearby bubbles whose padded boxes overlap must be filled
    in one pass, or the second fill paints over the first one's result
    using pixels that are themselves already synthetic.
    """
    width, height = size
    mask = np.zeros((height, width), dtype=np.uint8)
    for left, top, right, bottom in boxes:
        if right <= left or bottom <= top:
            continue
        mask[top:bottom, left:right] = 255
    return Image.fromarray(mask, mode="L")


def mask_is_empty(mask: Image.Image) -> bool:
    """True when nothing is marked for reconstruction. Worth checking
    before calling a remote service: sending it a blank mask costs a
    round trip to get the input image back unchanged.
    """
    return not np.asarray(mask).any()


class LocalInpainter:
    """OpenCV Telea. No weights, no network, no service to run.

    Kept as the default and the fallback rather than deleted. It is fast,
    it is deterministic, it is genuinely adequate on plain bubbles, and
    it means tests and local development need no infrastructure at all.
    """

    def __init__(self, radius: int = 3):
        self._radius = radius

    def inpaint(self, image: Image.Image, mask: Image.Image) -> Image.Image | None:
        try:
            import cv2

            # PIL is RGB, OpenCV wants BGR - a channel-order swap, not a
            # colour-space conversion, so this is loss-free both ways.
            # flatten_to_rgb, not a bare convert("RGB") - see that
            # function's docstring for why a naive convert on an image
            # that still carries alpha (this is a public Protocol method;
            # callers other than comics_redraw.py's already-flattened
            # image may pass one in directly) can leak uncomposited pixel
            # garbage through as a visible color shift.
            bgr = cv2.cvtColor(np.asarray(flatten_to_rgb(image)), cv2.COLOR_RGB2BGR)
            filled = cv2.inpaint(bgr, np.asarray(mask), self._radius, cv2.INPAINT_TELEA)
            return Image.fromarray(cv2.cvtColor(filled, cv2.COLOR_BGR2RGB))
        except ModuleNotFoundError:
            # Some environments do not bundle OpenCV. Return a plain
            # in-memory fallback instead of exploding the whole redraw
            # path: the result is less faithful than Telea, but it keeps
            # small panels and local development working.
            base = flatten_to_rgb(image)
            mask_array = np.asarray(mask.convert("L"), dtype=bool)
            pixels = np.asarray(base)
            if (~mask_array).any():
                fill = tuple(int(round(v)) for v in pixels[~mask_array].mean(axis=0))
            else:
                fill = tuple(int(round(v)) for v in pixels.reshape(-1, 3).mean(axis=0))
            return Image.composite(Image.new("RGB", base.size, fill), base, mask.convert("L"))
        except Exception as exc:  # noqa: BLE001 - degrade, never raise
            logger.warning("Local inpainting failed: %s", exc)
            return None


class RemoteInpainter:
    """A LaMa/IOPaint service over HTTP.

    Sends {"image": <b64 png>, "mask": <b64 png>} and accepts either raw
    image bytes or {"image": <b64>} back - IOPaint returns the former,
    and a thin custom wrapper around LaMa commonly returns the latter, so
    supporting both avoids forcing a particular server implementation.

    Any failure returns None and the caller falls back to local
    inpainting. That includes a reply whose dimensions don't match the
    input: a service that resized the panel would silently invalidate
    every bounding box the caller is about to typeset into, so it is
    safer to discard that result than to draw text at the wrong scale.

    A TRANSPORT failure (connection refused, timeout, DNS) gets
    config.INPAINT_MAX_RETRIES retries before giving up - a momentary
    network blip shouldn't permanently downgrade one redraw's quality
    when trying again is nearly free. A response the service actually
    returned (wrong dimensions, an unreadable body) is NOT retried -
    that's not the class of failure a retry fixes, and a broken
    integration would otherwise just retry into the same wrong answer.

    NOT VERIFIED AGAINST A REAL LaMa SERVICE in this repository - the
    weights live on Hugging Face, which this development environment
    blocks at the network layer. The adapter is written against
    IOPaint's documented request shape and tested against a stub. Treat
    reconstruction quality as unmeasured until it has been run against a
    real service on real artwork.
    """

    def __init__(self, url: str, timeout_seconds: float = 60.0, max_retries: int | None = None):
        self._url = url
        self._timeout = timeout_seconds
        # None (the default) reads config lazily rather than at import
        # time, same reasoning as build_inpainter() below - tests can
        # still pass an explicit value to avoid depending on env state.
        self._max_retries = max_retries

    def _resolved_max_retries(self) -> int:
        if self._max_retries is not None:
            return self._max_retries
        from . import config

        return config.INPAINT_MAX_RETRIES

    def inpaint(self, image: Image.Image, mask: Image.Image) -> Image.Image | None:
        import httpx

        payload = {
            "image": _encode_png(flatten_to_rgb(image)),
            "mask": _encode_png(mask.convert("L")),
        }
        attempts = 1 + max(0, self._resolved_max_retries())

        response = None
        for attempt in range(1, attempts + 1):
            try:
                response = httpx.post(self._url, json=payload, timeout=self._timeout)
                response.raise_for_status()
                break
            except Exception as exc:  # noqa: BLE001 - degrade, never raise
                if attempt < attempts:
                    logger.info(
                        "Remote inpainting attempt %d/%d failed (%s), retrying.",
                        attempt, attempts, exc,
                    )
                    continue
                logger.warning("Remote inpainting failed after %d attempt(s): %s", attempts, exc)
                return None

        result = _decode_response(response)
        if result is None:
            return None
        if result.size != image.size:
            logger.warning(
                "Remote inpainter returned %s for a %s panel; discarding - every "
                "bounding box would be at the wrong scale.",
                result.size,
                image.size,
            )
            return None
        return result


def _encode_png(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _decode_response(response) -> Image.Image | None:
    """Accepts either raw image bytes or a JSON body carrying base64.

    Content-Type is checked first but not trusted as the only signal -
    a service that mislabels its response is common enough that falling
    back to just trying to open the body is worth the few lines.
    """
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("image/"):
        return _open_image(response.content)

    try:
        payload = response.json()
    except Exception:  # noqa: BLE001 - not JSON; try the body as an image
        return _open_image(response.content)

    if isinstance(payload, dict):
        for key in ("image", "result", "output"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                try:
                    return _open_image(base64.b64decode(value))
                except Exception:  # noqa: BLE001
                    continue
    return None


def _open_image(data: bytes) -> Image.Image | None:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        return flatten_to_rgb(image)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Inpainter reply was not a readable image: %s", exc)
        return None


def build_inpainter() -> Inpainter:
    """The configured remote service when CASTIA_INPAINT_URL is set,
    otherwise local OpenCV.

    Note this returns the REMOTE inpainter without probing it. Health-
    checking here would add a round trip to every redraw to guard against
    a failure the call itself already handles by returning None.
    """
    from . import config

    if config.INPAINT_URL:
        return RemoteInpainter(config.INPAINT_URL, config.INPAINT_TIMEOUT_SECONDS)
    return LocalInpainter()


def inpaint_with_fallback(
    image: Image.Image,
    mask: Image.Image,
    inpainter: Inpainter | None = None,
) -> tuple[Image.Image, str]:
    """Runs the configured inpainter, falling back to local OpenCV if it
    declines, and reports which one actually produced the result.

    Returns (image, method) where method is "remote", "local", or "none".
    "none" means even local inpainting failed, in which case the ORIGINAL
    image comes back untouched - the caller then draws over un-erased
    text, which looks wrong but is honest and still lets the human see
    what happened, unlike a blank or half-processed panel.
    """
    if mask_is_empty(mask):
        return image, "none"

    inpainter = inpainter or build_inpainter()
    is_remote = isinstance(inpainter, RemoteInpainter)

    result = inpainter.inpaint(image, mask)
    if result is not None:
        return result, "remote" if is_remote else "local"

    if is_remote:
        logger.info("Falling back to local inpainting for this panel.")
        local = LocalInpainter().inpaint(image, mask)
        if local is not None:
            return local, "local"

    return image, "none"
