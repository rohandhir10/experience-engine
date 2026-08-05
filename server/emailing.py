"""Outbound transactional email - today, exactly one message type
(email/password sign-up verification, server/password_auth.py).

No real provider is wired up yet (no Resend/Postmark/SES account exists
for this project), so `send_verification_email` degrades the same way
server/paddle.py degrades without real Paddle credentials: it does the
real, correct thing up to the point that requires a paid third party,
then logs instead of silently pretending to succeed. Logging the actual
verify link (not just "an email would be sent") is deliberate - it's what
makes the flow testable end-to-end (locally, in CI, in this deployment)
before a provider is chosen, without a fake/mocked send path that could
drift from what a real integration will need to do.

Wiring a real provider later is meant to be a change contained to this
one file: keep the same function signature, replace the log call with an
HTTP call to whichever provider is chosen, gated behind that provider's
own env var (e.g. RESEND_API_KEY) the same way PADDLE_WEBHOOK_SECRET
gates server/paddle.py.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("castia.emailing")

# Where the Next.js app lives, for building a clickable verification
# link server-side - the Python API has no other reason to know this
# today. Defaults to the real production origin (web/lib/seo.ts's
# SITE_URL) so a log line is a genuinely usable link even before this
# env var is explicitly set on a given deployment.
WEB_APP_URL = os.environ.get("CASTIA_WEB_APP_URL", "https://usecastia.com")


def verification_link(token: str) -> str:
    return f"{WEB_APP_URL}/verify-email?token={token}"


def send_verification_email(to_email: str, token: str) -> None:
    """Called once per registration/resend with a freshly minted raw
    token (server/password_auth.py holds only its hash - this is the one
    place the raw value exists outside the user's inbox). Never raises:
    a delivery failure here should never take down a signup request that
    otherwise succeeded - see the module docstring on why this currently
    always "fails" over to logging.
    """
    link = verification_link(token)
    logger.info(
        "verification email (no provider configured - not actually sent): "
        "to=%s subject=%r link=%s",
        to_email,
        "Verify your email for Castia",
        link,
    )
