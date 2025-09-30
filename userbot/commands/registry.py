"""Registrasi command userbot."""
from __future__ import annotations

from typing import Dict

try:
    from .base import CommandSpec
except ImportError:
    from commands.base import CommandSpec


COMMANDS: Dict[str, CommandSpec] = {}


def register(command: CommandSpec) -> None:
    COMMANDS[command.name] = command


def get_commands() -> Dict[str, CommandSpec]:
    return COMMANDS

