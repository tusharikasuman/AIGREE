"""FastAPI app. Run: uvicorn app.main:app --reload --port 8000 (from backend/)."""

import logging
import os
from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .analyzer import AnalysisError, Analyzer
from .schemas import AnalysisResult, AnalyzeRequest
from .scraper import ScrapeError, scrape_url

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aigree")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.analyzer = None  # created lazily so the server starts even without an API key
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        log.warning("ANTHROPIC_API_KEY is not set. Add it to backend/.env or /analyze will fail.")
    yield


app = FastAPI(title="AIGREE - T&C Analyzer", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def get_analyzer() -> Analyzer:
    if app.state.analyzer is None:
        app.state.analyzer = Analyzer()
    return app.state.analyzer


@app.get("/health")
async def health():
    return {"status": "ok", "model": config.MODEL}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(req: AnalyzeRequest) -> AnalysisResult:
    if req.url:
        try:
            text = await scrape_url(str(req.url))
        except ScrapeError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        text = req.text or ""

    try:
        return await get_analyzer().analyze(text)
    except AnalysisError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="Server misconfigured: invalid or missing ANTHROPIC_API_KEY.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Too many requests to the AI service. Try again in a minute.")
    except anthropic.BadRequestError as e:
        log.error("Claude rejected the request: %s", e.message)
        raise HTTPException(status_code=502, detail=f"The AI service rejected the request: {e.message}")
    except anthropic.APIStatusError as e:
        log.error("Claude API error %s: %s", e.status_code, e.message)
        raise HTTPException(status_code=502, detail="The AI service returned an error. Try again shortly.")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not reach the AI service. Check the server's connection.")
    except anthropic.AnthropicError as e:
        log.error("Anthropic client error: %s", e)
        raise HTTPException(status_code=500, detail="The AI client failed. Check the server logs.")
    except TypeError as e:
        # The SDK raises TypeError when no credentials are configured at all.
        if "authentication" not in str(e).lower():
            raise
        raise HTTPException(status_code=500, detail="Server misconfigured: set ANTHROPIC_API_KEY in backend/.env.")
