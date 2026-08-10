"""Tests for server/main.py::production_config_problems.

Everything it checks is a SILENT failure: the service starts healthy and
serves traffic, and the damage only surfaces later as a purchase that
granted nothing, verification mail nobody received, or quota counters
that reset on every deploy. A startup warning is the cheapest place to
catch a deploy missing an environment variable, so these tests pin down
that each one is actually detected - and, just as importantly, that a
fully-configured deployment reports nothing (a check that always fires is
a check everyone learns to ignore).
"""
from __future__ import annotations

import pytest

import server.main as main


FULLY_CONFIGURED = {
    "DATABASE_URL": "postgresql://user:pw@localhost/castia",
    "RESEND_API_KEY": "re_live_xxx",
    "CASTIA_PADDLE_WEBHOOK_SECRET": "pdl_ntfset_xxx",
    "CASTIA_PADDLE_PRICE_CREDITS": '{"pri_123": 144}',
}


@pytest.fixture
def configured(monkeypatch):
    """A deployment with everything set correctly."""
    for key, value in FULLY_CONFIGURED.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "internal-secret")
    monkeypatch.setattr(main.emailing, "EMAIL_FROM", "Castia <hello@castia.app>")


def test_a_fully_configured_deployment_reports_nothing(configured):
    assert main.production_config_problems() == []


def test_missing_database_url_is_reported(configured, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    problems = main.production_config_problems()
    assert any("DATABASE_URL" in p for p in problems)


def test_missing_internal_secret_is_reported(configured, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "")
    problems = main.production_config_problems()
    assert any("CASTIA_INTERNAL_API_SECRET" in p for p in problems)


def test_missing_resend_key_is_reported(configured, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY")
    problems = main.production_config_problems()
    assert any("RESEND_API_KEY" in p for p in problems)


def test_the_resend_sandbox_sender_is_reported(configured, monkeypatch):
    """The default in server/emailing.py is Resend's own sandbox address.
    It works, which is exactly why it's easy to ship by accident - and
    mail from it is likely to be filtered."""
    monkeypatch.setattr(main.emailing, "EMAIL_FROM", "Castia <onboarding@resend.dev>")
    problems = main.production_config_problems()
    assert any("resend.dev" in p for p in problems)


def test_the_sandbox_sender_is_not_reported_when_mail_cannot_send_at_all(
    configured, monkeypatch
):
    """With no API key nothing is delivered regardless of sender, so
    naming the sender too would be noise on top of the real problem."""
    monkeypatch.delenv("RESEND_API_KEY")
    monkeypatch.setattr(main.emailing, "EMAIL_FROM", "Castia <onboarding@resend.dev>")
    problems = main.production_config_problems()
    assert any("RESEND_API_KEY" in p for p in problems)
    assert not any("resend.dev" in p for p in problems)


def test_missing_paddle_webhook_secret_is_reported(configured, monkeypatch):
    monkeypatch.delenv("CASTIA_PADDLE_WEBHOOK_SECRET")
    problems = main.production_config_problems()
    assert any("CASTIA_PADDLE_WEBHOOK_SECRET" in p for p in problems)


def test_paddle_configured_but_with_no_price_mapping_is_reported(configured, monkeypatch):
    """The nastiest of the set: signatures verify, the webhook returns
    200, Paddle sees success - and the customer's credits never arrive."""
    monkeypatch.delenv("CASTIA_PADDLE_PRICE_CREDITS")
    problems = main.production_config_problems()
    assert any("CASTIA_PADDLE_PRICE_CREDITS" in p for p in problems)


def test_the_price_mapping_is_not_reported_when_the_webhook_is_off_entirely(
    configured, monkeypatch
):
    monkeypatch.delenv("CASTIA_PADDLE_WEBHOOK_SECRET")
    monkeypatch.delenv("CASTIA_PADDLE_PRICE_CREDITS")
    problems = main.production_config_problems()
    assert any("CASTIA_PADDLE_WEBHOOK_SECRET" in p for p in problems)
    assert not any("CASTIA_PADDLE_PRICE_CREDITS" in p for p in problems)


def test_every_problem_names_the_variable_and_the_real_consequence(monkeypatch):
    """A warning that says only "misconfigured" gets ignored. Each line
    has to say what to set and what actually breaks without it."""
    for key in FULLY_CONFIGURED:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "")

    problems = main.production_config_problems()
    assert len(problems) >= 4
    for problem in problems:
        assert any(c.isupper() for c in problem), problem  # names a variable
        assert len(problem) > 80, problem  # explains a consequence, not just a name


def test_never_raises_even_with_a_completely_empty_environment(monkeypatch):
    """This runs inside the startup lifespan - a warning that could crash
    the process would be worse than the misconfiguration it reports."""
    for key in FULLY_CONFIGURED:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "")
    assert isinstance(main.production_config_problems(), list)
