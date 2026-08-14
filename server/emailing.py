"""Outbound transactional email - two message types today, both from
server/password_auth.py: sign-up verification and password reset.

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


def password_reset_link(token: str) -> str:
    return f"{WEB_APP_URL}/reset-password?token={token}"


def _verification_email_html(link: str) -> str:
    return (
        "<p>Verify your email for Castia by clicking the link below:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>If you didn't sign up for Castia, you can ignore this email.</p>"
    )


def _password_reset_email_html(link: str) -> str:
    return (
        "<p>Reset your Castia password by clicking the link below. "
        "This link expires in 1 hour.</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>If you didn't request this, you can ignore this email - your "
        "password won't change unless you click the link above and "
        "choose a new one.</p>"
    )


def _send(to_email: str, subject: str, html: str, link: str) -> None:
    """Shared Resend call for every message type this module sends.
    Never raises: a delivery failure here should never take down the
    request that triggered it, so a Resend error is logged, not
    propagated - see the module docstring for why this degrades to
    logging instead of silently pretending to succeed. `link` is passed
    separately (rather than re-extracted from `html`) purely so the
    no-provider/failure log lines below can print it plainly.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.info(
            "%s (RESEND_API_KEY not set - not actually sent): to=%s link=%s",
            subject,
            to_email,
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
                "html": html,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        # Deliberately no link/token in this line - once a real send
        # succeeds, the raw link shouldn't linger in server logs the way
        # it does in the no-provider fallback above, which only ever logs
        # it because logging IS the delivery mechanism at that point.
        logger.info("%s sent via Resend: to=%s", subject, to_email)
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        # Still logs the link on failure - a delivery error must not
        # strand the user with no way to act, so the same fallback the
        # no-provider path always offers stays available here too.
        logger.warning(
            "%s failed to send via Resend (%s): to=%s link=%s",
            subject,
            exc,
            to_email,
            link,
        )


def send_verification_email(to_email: str, token: str) -> None:
    """Called once per registration/resend with a freshly minted raw
    token (server/password_auth.py holds only its hash - this is the one
    place the raw value exists outside the user's inbox)."""
    link = verification_link(token)
    _send(to_email, "Verify your email for Castia", _verification_email_html(link), link)


def send_password_reset_email(to_email: str, token: str) -> None:
    """Called once per forgot-password request with a freshly minted raw
    token (server/password_auth.py holds only its hash - this is the one
    place the raw value exists outside the user's inbox)."""
    link = password_reset_link(token)
    _send(to_email, "Reset your Castia password", _password_reset_email_html(link), link)
