"""FastAPI app. Run: uvicorn app.main:app --reload --port 8000 (from backend/)."""

import logging
from contextlib import asynccontextmanager

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
    log.info("Provider: %s | model: %s", config.PROVIDER, config.MODEL)
    if config.PROVIDER != "ollama" and not config.API_KEY:
        log.warning("No API key set for provider '%s'. Add it to backend/.env.", config.PROVIDER)
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
    return {"status": "ok", "provider": config.PROVIDER, "model": config.MODEL}


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
