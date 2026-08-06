"""Outbound transactional email - today, exactly one message type
(email/password sign-up verification, server/password_auth.py).

Sends via Resend (https://resend.com) when RESEND_API_KEY is set, the
same opt-in-via-env-var convention PADDLE_WEBHOOK_SECRET already
established for server/paddle.py: real behavior gated behind a real
credential, degrading to logging (never raising, never silently
pretending to succeed) when that credential is absent - local dev, CI,
and any deployment that hasn't configured Resend yet all keep working
without a fake/mocked send path that could drift from what the real
integration actually does.
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

RESEND_API_URL = "https://api.resend.com/emails"

# Resend's own shared testing sender - deliverable with zero setup, but
# only to the account's own verified email during Resend's sandbox mode,
# and it visibly isn't castia's domain. Meant to be overridden with a
# verified-domain address (e.g. "Castia <noreply@usecastia.com>") once a
# real domain is verified in the Resend dashboard - that verification is
# a real action outside this codebase, not something a code change can
# do on its own.
EMAIL_FROM = os.environ.get("CASTIA_EMAIL_FROM", "Castia <onboarding@resend.dev>")


def verification_link(token: str) -> str:
    return f"{WEB_APP_URL}/verify-email?token={token}"


def _verification_email_html(link: str) -> str:
    return (
        "<p>Verify your email for Castia by clicking the link below:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>If you didn't sign up for Castia, you can ignore this email.</p>"
    )


def send_verification_email(to_email: str, token: str) -> None:
    """Called once per registration/resend with a freshly minted raw
    token (server/password_auth.py holds only its hash - this is the one
    place the raw value exists outside the user's inbox). Never raises:
    a delivery failure here should never take down a signup request that
    otherwise succeeded, so a Resend error is logged, not propagated -
    see the module docstring for why this degrades to logging instead of
    silently pretending to succeed.
    """
    link = verification_link(token)
    subject = "Verify your email for Castia"

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.info(
            "verification email (RESEND_API_KEY not set - not actually sent): "
            "to=%s subject=%r link=%s",
            to_email,
            subject,
            link,
        )
        return

    import httpx

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "html": _verification_email_html(link),
            },
            timeout=10.0,
        )
        response.raise_for_status()
        # Deliberately no link/token in this line - once a real send
        # succeeds, the raw verification link shouldn't linger in server
        # logs the way it does in the no-provider fallback above, which
        # only ever logs it because logging IS the delivery mechanism at
        # that point.
        logger.info("verification email sent via Resend: to=%s", to_email)
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        # Still logs the link on failure - a delivery error must not
        # strand the user with no way to verify, so the same fallback the
        # no-provider path always offers stays available here too.
        logger.warning(
            "verification email failed to send via Resend (%s): to=%s subject=%r link=%s",
            exc,
            to_email,
            subject,
            link,
        )
