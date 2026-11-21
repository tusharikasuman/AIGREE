"""Fetch a URL and pull out the main text with Trafilatura."""

import asyncio

import trafilatura


class ScrapeError(Exception):
    pass


def _scrape_sync(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ScrapeError(f"Could not download {url}. The site may block bots or be unreachable.")
    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        favor_recall=True,  # T&C pages are long; prefer keeping text over dropping it
    )
    if not text or not text.strip():
        raise ScrapeError(
            "No readable text found at that URL. It may be rendered with JavaScript; "
            "paste the text instead."
        )
    return text


async def scrape_url(url: str) -> str:
    # trafilatura is synchronous; keep it off the event loop.
    return await asyncio.to_thread(_scrape_sync, url)
