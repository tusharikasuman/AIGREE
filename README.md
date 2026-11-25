# AIGREE: know what you're agreeing to

Paste Terms & Conditions (or a link) and get a plain-language summary, a 0-100 trust score with an A-E grade, four sub-scores, and each red flag with its quote, its effect on the score, and what you can do about it.

- **Backend:** FastAPI + Trafilatura + your choice of AI: Google Gemini (free tier), local Qwen via Ollama (free, slow on CPU), OpenAI or any OpenAI-compatible API, or Claude
- **Browser extension** (`extension/`, Phase 2): answers cookie banners for you (**Necessary only** or **Accept all**) and shows the trust score for the site you're on. See [extension/README.md](extension/README.md).
- **Web app** (`frontend/`): Next.js 15 + Tailwind CSS, for pasting text or a link

## Folder structure

```
aigree/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app: POST /analyze, GET /health, error mapping
│   │   ├── analyzer.py      # chunk -> LLM per chunk -> validate/retry -> verify quotes -> merge
│   │   ├── providers.py     # Ollama / OpenAI-compatible / Claude backends
│   │   ├── schemas.py       # Pydantic models + JSON schemas sent to the model
│   │   ├── checklist.py     # the red-flag checklist and its weights
│   │   ├── scoring.py       # findings -> score, sub-scores, grade (no AI)
│   │   ├── chunker.py       # paragraph-aware splitting with overlap
│   │   ├── scraper.py       # Trafilatura URL -> main text
│   │   ├── prompts.py       # loads the prompt files
│   │   └── config.py        # env-var settings
│   ├── prompts/
│   │   ├── system_prompt.md # main analysis prompt ({{CHECKLIST}} is filled in from checklist.py)
│   │   └── merge_prompt.md  # one summary for long documents
│   ├── samples/sample_tos.txt   # fictional "StreamNest" T&C for testing
│   ├── scripts/run_sample.py    # CLI: analyze a file or URL, print JSON
│   ├── Dockerfile
│   └── requirements.txt
├── extension/               # Chrome/Edge extension (WXT + React, Manifest V3)
├── frontend/
│   ├── app/                 # layout.tsx, page.tsx (input + loading/error/results), globals.css
│   ├── components/          # ScoreRing, SubScores, ClauseList, Results
│   ├── lib/                 # api.ts (types + fetch), colors.ts (score bands, tier colours)
│   └── .env.local.example
└── docker-compose.yml
```

## How it works

1. `POST /analyze` takes `{"text": "..."}` **or** `{"url": "..."}`. URLs are scraped with Trafilatura.
2. Text is normalised and split into chunks (12k characters for local models, 30k for cloud APIs) on paragraph boundaries, with 500 characters of overlap so that a clause on a boundary is seen whole.
3. Each chunk goes to the model with the JSON schema enforced (Ollama `format`, OpenAI `response_format`, or Claude structured output). The model **doesn't score anything**: it reports which items from a fixed red-flag checklist the text contains, each with an exact quote. It also says whether the text is terms at all; if not, the request fails with 422 instead of returning a score.
4. The response is validated with **Pydantic** (known checklist ids, category list, summary under 150 words). If validation fails, the error is sent back to the model and the request is **retried once**.
5. Every `original_text` is checked against the source document. Quotes that don't appear in it are dropped: no quote, no points.
6. For multi-chunk documents, a merge call writes one summary. Findings are de-duplicated in code.
7. The score is calculated in code (`backend/app/scoring.py`), so the same findings always give the same score.

### Scoring

The checklist and weights live in `backend/app/checklist.py` (the AI prompt is generated from it).

- Every document starts at **100**. Each checklist item found changes it by a fixed amount:
  - **Serious, −15:** for example sells your data, trains AI on your content, cancel fee, hard to cancel.
  - **Notable, −8:** for example forced arbitration, auto-renewal, no refunds, can close your account without reason.
  - **Standard, −3:** for example governing law/venue, liability limits. These are in almost all terms.
  - **Good sign, +5:** for example never sells data, cancel any time, data export.
- Concerns that aren't on the checklist count −8 (high) or −3 (medium), at most −15 in total.
- One serious red flag limits the score to 69 (grade C). Two or more limit it to 54 (grade D).
- An A needs at least one good sign: terms that only avoid red flags get at most 84 (B).
- Each sub-score counts its own area's points double.
- Grades: **A** 85+ · **B** 70-84 · **C** 55-69 · **D** 40-54 · **E** below 40.

Higher = better for the user (`financial_risk: 90` means *low* financial risk). The response includes `score_notes`, which explain the calculation in words.

## Run it

Needs Python 3.10+ and Node 18.18+ (or just Docker), plus an AI provider. The quickest free option is a [Google AI Studio](https://aistudio.google.com/apikey) API key. Create `backend/.env`:

```ini
AIGREE_PROVIDER=openai
AIGREE_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
AIGREE_MODEL=gemini-flash-lite-latest
AIGREE_JSON_MODE=json_schema
AIGREE_FALLBACK_MODEL=gemini-3.5-flash
AIGREE_API_KEY=your-key-here
```

`backend/.env` is git-ignored; never commit it. Other providers are listed under [Choosing the AI](#choosing-the-ai-backendenv). A cloud API takes seconds; a local model on a laptop CPU takes minutes.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# create backend/.env first (see above)
uvicorn app.main:app --reload --port 8000
```

Check it: <http://localhost:8000/health> · interactive API docs: <http://localhost:8000/docs>

### 2. Frontend

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open <http://localhost:3000>.

### Docker

If you use Ollama, start it on your PC first (it stays on the host). Then:

```powershell
docker compose up -d --build backend    # backend only
docker compose up -d --build            # backend + frontend
docker compose logs -f backend
docker compose down
```

The backend reads `backend/.env` and reaches the host's Ollama at `http://host.docker.internal:11434` (set via `AIGREE_OLLAMA_URL`). The frontend is a production build. `NEXT_PUBLIC_API_URL` is baked in at build time (default `http://localhost:8000`), so rebuild after changing it.

### CLI

```powershell
cd backend
python -m scripts.run_sample                  # live: analyzes samples/sample_tos.txt
python -m scripts.run_sample https://www.mozilla.org/en-US/about/legal/terms/mozilla/
```

```bash
curl -X POST localhost:8000/analyze -H "Content-Type: application/json" \
  -d '{"url": "https://www.mozilla.org/en-US/about/legal/terms/mozilla/"}'
```

## Choosing the AI (`backend/.env`)

| Option | Cost | Settings |
|---|---|---|
| **Google Gemini** | Free tier (often busy: requests are retried, then the fallback model is tried) | See [Run it](#run-it) |
| **Local Qwen (Ollama)** | Free, runs on your PC (slow on CPU) | `AIGREE_PROVIDER=ollama`, `AIGREE_MODEL=qwen2.5:3b` (run `ollama pull qwen2.5:3b` first) |
| **OpenAI** | Paid (prepaid credits) | `AIGREE_PROVIDER=openai`, `AIGREE_MODEL=gpt-4o-mini`, `AIGREE_API_KEY=sk-...` |
| **Qwen on Alibaba Model Studio** | Free quota for new accounts, then paid | `AIGREE_PROVIDER=openai`, `AIGREE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, `AIGREE_MODEL=qwen-plus`, `AIGREE_JSON_MODE=json_object`, `AIGREE_API_KEY=...` |
| **OpenRouter** | Some `:free` models | `AIGREE_PROVIDER=openai`, `AIGREE_BASE_URL=https://openrouter.ai/api/v1`, `AIGREE_MODEL=<id>`, `AIGREE_JSON_MODE=json_object`, `AIGREE_API_KEY=...` |
| **Claude** | Paid | `AIGREE_PROVIDER=claude`, `AIGREE_API_KEY=sk-ant-...` (model `claude-opus-5-5`) |

Other settings:

| Variable | Default | Notes |
|---|---|---|
| `AIGREE_TIMEOUT_SECONDS` | 1200 (ollama) / 300 / 600 | Per request |
| `AIGREE_OLLAMA_NUM_CTX` | `8192` | Ollama context window |
| `AIGREE_OLLAMA_THINK` | model default | Set `false` for thinking models like `qwen3.5` to make them faster |
| `AIGREE_JSON_MODE` | `json_schema` | Use `json_object` for APIs without strict schema support |
| `AIGREE_MAX_RETRIES` | `5` | Retries with backoff when the AI service is busy (OpenAI-compatible APIs) |
| `AIGREE_FALLBACK_MODEL` | none | Tried once if the main model is still busy (429/503) after retries |
| `AIGREE_EFFORT` / `AIGREE_USE_FALLBACKS` | `medium` / `true` | Claude only |
| `AIGREE_CHUNK_CHARS` | 12000 (ollama) / 30000 | Chunk size |
| `AIGREE_MAX_INPUT_CHARS` | `400000` | Larger inputs are rejected (413) |
| `AIGREE_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |

Restart the backend after editing `.env`. With Docker, use `docker compose up -d --force-recreate backend`. A plain `restart` keeps the old settings.

## Tuning the AI

- **What counts and how much:** edit `CHECKS` and the weights in `backend/app/checklist.py`. The prompt's checklist is generated from it, so there's nothing else to update.
- **How the AI reports findings:** edit `backend/prompts/system_prompt.md`.

Restart the backend afterwards (with Docker: `docker compose up -d --build backend`).

## API errors

| Status | Meaning |
|---|---|
| 400 | Text too short |
| 413 | Document too long |
| 422 | Not a terms document (no score is given), bad input (both or neither of text/url), URL couldn't be scraped, or the AI declined |
| 429 | Rate-limited by the AI service |
| 500 | API key missing/invalid, or the Ollama model isn't downloaded |
| 502 / 503 / 504 | AI service error, malformed output twice, unreachable (e.g. Ollama not running), or timed out |

*AI-generated analysis is for information only. It is not legal advice.*
