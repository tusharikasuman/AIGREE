"""Split long documents into overlapping chunks on paragraph/sentence boundaries."""

import re


def normalize(text: str) -> str:
    """Collapse runs of spaces/tabs and 3+ newlines; keep paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _best_cut(text: str, start: int, hard_end: int) -> int:
    """Pick a cut point at or before hard_end: paragraph > line > sentence > space."""
    window_start = start + (hard_end - start) // 2  # never cut in the first half
    for sep in ("\n\n", "\n", ". ", " "):
        idx = text.rfind(sep, window_start, hard_end)
        if idx != -1:
            return idx + len(sep)
    return hard_end


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        hard_end = start + max_chars
        if hard_end >= len(text):
            chunks.append(text[start:].strip())
            break
        cut = _best_cut(text, start, hard_end)
        chunks.append(text[start:cut].strip())
        # Overlap so a clause sitting on a boundary is seen whole by one chunk.
        start = max(cut - overlap, start + 1)
    return [c for c in chunks if c]
