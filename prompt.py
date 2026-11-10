"""Render the full prompt from a profile."""
from __future__ import annotations

from pathlib import Path
from user_profile import Profile


def build_prompt(profile: Profile) -> str:
    template = (Path(__file__).parent / "prompt_template.md").read_text(encoding="utf-8")
    return template.replace("{{FOR_BLOCK}}", profile.for_block())
