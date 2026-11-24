"""Load prompt files from backend/prompts/. Edit the .md files to tweak behaviour."""

from functools import lru_cache

from .config import PROMPTS_DIR


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


@lru_cache
def system_prompt() -> str:
    from .checklist import prompt_table

    return load_prompt("system_prompt.md").replace("{{CHECKLIST}}", prompt_table())


def merge_prompt() -> str:
    return load_prompt("merge_prompt.md")
