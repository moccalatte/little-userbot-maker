"""Wizard bot composition built from modular mixins."""
from __future__ import annotations

from ..config import BotSettings
from .admin_mixin import AdminMixin
from .base import WizardBase
from .entry_mixin import EntryMixin
from .login_mixin import LoginMixin
from .session_mixin import SessionMixin
from .userbot_mixin import UserbotMixin


class WizardBot(EntryMixin, LoginMixin, SessionMixin, AdminMixin, UserbotMixin, WizardBase):
    """Concrete bot implementation assembled from reusable pieces."""

    def __init__(self, settings: BotSettings) -> None:
        super().__init__(settings)


def run_bot(settings: BotSettings) -> None:
    bot = WizardBot(settings)
    app = bot.build_application()
    app.run_polling()


__all__ = ["WizardBot", "run_bot"]
