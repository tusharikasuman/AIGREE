"""Load prompt files from backend/prompts/. Edit the .md files to tweak behaviour."""

from functools import lru_cache

from .config import PROMPTS_DIR


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def system_prompt() -> str:
    return load_prompt("system_prompt.md")


def merge_prompt() -> str:
    return load_prompt("merge_prompt.md")
