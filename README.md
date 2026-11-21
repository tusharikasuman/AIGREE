# AIGREE: T&C Analyzer (Phase 1)

Paste Terms & Conditions (or a link) and get a plain-language summary, a 0-100 trust score, four sub-scores, and the risky clauses highlighted by severity.

- **Backend:** FastAPI + Claude API (`claude-opus-5-5`) + Trafilatura
- **Frontend:** Next.js 15 + Tailwind CSS

## Folder structure

```
aigree/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app: POST /analyze, GET /health, error mapping
│   │   ├── analyzer.py      # chunk -> Claude per chunk -> validate/retry -> verify quotes -> merge
│   │   ├── schemas.py       # Pydantic models + JSON schemas sent to Claude
│   │   ├── chunker.py       # paragraph-aware splitting with overlap
│   │   ├── scraper.py       # Trafilatura URL -> main text
│   │   ├── prompts.py       # loads the prompt files
│   │   └── config.py        # env-var settings
│   ├── prompts/
│   │   ├── system_prompt.md # main analysis prompt, edit to tune behaviour
│   │   └── merge_prompt.md  # combines per-chunk results for long documents
│   ├── samples/sample_tos.txt   # fictional "StreamNest" T&C for testing
│   ├── scripts/run_sample.py    # CLI: analyze a file or URL, print JSON
│   ├── tests/test_analyzer.py   # offline tests with a fake Claude client
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/                 # layout.tsx, page.tsx (input + loading/error/results), globals.css
    ├── components/          # ScoreRing, SubScores, ClauseList, Results
    ├── lib/                 # api.ts (types + fetch), colors.ts (score bands, severity colours)
    └── .env.local.example
```

## How it works

1. `POST /analyze` takes `{"text": "..."}` **or** `{"url": "..."}`. URLs are scraped with Trafilatura.
2. Text is normalised and split into ~30k-character chunks on paragraph boundaries, with 500 characters of overlap so that a clause on a boundary is seen whole.
3. Each chunk goes to Claude in parallel, using **structured output** (a JSON schema), so the response is well-formed JSON.
4. The response is validated with **Pydantic** (score ranges, severity values, category list, summary under 150 words). If validation fails, the error is sent back to Claude and the request is **retried once**.
5. Every `original_text` is checked against the source document. Quotes that don't appear in it are dropped, so the app never shows a clause the document doesn't contain.
6. For multi-chunk documents, a merge call writes one summary and one set of scores. Clauses are de-duplicated and sorted by severity in code.

Scores: **higher = better for the user** (`financial_risk: 90` means *low* financial risk).

## Run it

Needs Python 3.10+ and Node 18.18+.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...
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

### Tests and CLI

```powershell
cd backend
python -m pytest                              # offline, no API key needed
python -m scripts.run_sample                  # live: analyzes samples/sample_tos.txt
python -m scripts.run_sample https://www.mozilla.org/en-US/about/legal/terms/mozilla/
```

```bash
curl -X POST localhost:8000/analyze -H "Content-Type: application/json" \
  -d '{"url": "https://www.mozilla.org/en-US/about/legal/terms/mozilla/"}'
```

## Configuration (`backend/.env`)

| Variable | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Required |
| `AIGREE_MODEL` | `claude-opus-5-5` | |
| `AIGREE_EFFORT` | `medium` | `low`/`medium`/`high`/`xhigh`/`max`: more effort means deeper analysis but is slower and costs more |
| `AIGREE_USE_FALLBACKS` | `true` | If Claude declines a request, the API retries it on a fallback model in the same call |
| `AIGREE_CHUNK_CHARS` | `30000` | Chunk size |
| `AIGREE_MAX_INPUT_CHARS` | `400000` | Larger inputs are rejected (413) |
| `AIGREE_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |

## Tuning the AI

Edit `backend/prompts/system_prompt.md` (the categories, severity rules and scoring rubric) and restart the server. If you change the category list, also update `Category` in `backend/app/schemas.py`.

## API errors

| Status | Meaning |
|---|---|
| 400 | Text too short |
| 413 | Document too long |
| 422 | Bad input (both or neither of text/url), URL couldn't be scraped, or the AI declined |
| 429 | Rate-limited by the AI service |
| 500 | API key missing or invalid |
| 502 / 503 | AI service error, malformed output twice, or unreachable |

*AI-generated analysis is for information only. It is not legal advice.*
