# AIGREE: T&C Analyzer (Phase 1)

Paste Terms & Conditions (or a link) and get a plain-language summary, a 0-100 trust score, four sub-scores, and the risky clauses highlighted by severity.

- **Backend:** FastAPI + Trafilatura + your choice of AI: **local Qwen via Ollama (free, default)**, OpenAI or any OpenAI-compatible API (Alibaba Qwen, OpenRouter), or Claude
- **Frontend:** Next.js 15 + Tailwind CSS

## Folder structure

```
aigree/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app: POST /analyze, GET /health, error mapping
│   │   ├── analyzer.py      # chunk -> LLM per chunk -> validate/retry -> verify quotes -> merge
│   │   ├── providers.py     # Ollama / OpenAI-compatible / Claude backends
│   │   ├── schemas.py       # Pydantic models + JSON schemas sent to the model
│   │   ├── chunker.py       # paragraph-aware splitting with overlap
│   │   ├── scraper.py       # Trafilatura URL -> main text
│   │   ├── prompts.py       # loads the prompt files
│   │   └── config.py        # env-var settings
│   ├── prompts/
│   │   ├── system_prompt.md # main analysis prompt, edit to tune behaviour
│   │   └── merge_prompt.md  # combines per-chunk results for long documents
│   ├── samples/sample_tos.txt   # fictional "StreamNest" T&C for testing
│   ├── scripts/run_sample.py    # CLI: analyze a file or URL, print JSON
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
2. Text is normalised and split into chunks (12k characters for local models, 30k for cloud APIs) on paragraph boundaries, with 500 characters of overlap so that a clause on a boundary is seen whole.
3. Each chunk goes to the model with the JSON schema enforced (Ollama `format`, OpenAI `response_format`, or Claude structured output).
4. The response is validated with **Pydantic** (score ranges, severity values, category list, summary under 150 words). If validation fails, the error is sent back to the model and the request is **retried once**.
5. Every `original_text` is checked against the source document. Quotes that don't appear in it are dropped, so the app never shows a clause the document doesn't contain.
6. For multi-chunk documents, a merge call writes one summary and one set of scores. Clauses are de-duplicated and sorted by severity in code.

Scores: **higher = better for the user** (`financial_risk: 90` means *low* financial risk).

## Run it

Needs Python 3.10+, Node 18.18+, and (for the free default) [Ollama](https://ollama.com) with a Qwen model:

```powershell
ollama pull qwen2.5:3b
```

On a laptop CPU a local analysis takes a few minutes. A cloud API takes seconds.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
# default: local Qwen via Ollama. For another provider, edit .env (see below)
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

`backend/.env.example` has ready-to-uncomment blocks for each option.

| Option | Cost | Settings |
|---|---|---|
| **Local Qwen (Ollama)**, the default | Free, runs on your PC (slow on CPU) | `AIGREE_PROVIDER=ollama`, `AIGREE_MODEL=qwen2.5:3b` |
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
| `AIGREE_EFFORT` / `AIGREE_USE_FALLBACKS` | `medium` / `true` | Claude only |
| `AIGREE_CHUNK_CHARS` | 12000 (ollama) / 30000 | Chunk size |
| `AIGREE_MAX_INPUT_CHARS` | `400000` | Larger inputs are rejected (413) |
| `AIGREE_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |

Restart the backend after editing `.env`.

## Tuning the AI

Edit `backend/prompts/system_prompt.md` (the categories, severity rules and scoring rubric) and restart the server. If you change the category list, also update `Category` in `backend/app/schemas.py`.

## API errors

| Status | Meaning |
|---|---|
| 400 | Text too short |
| 413 | Document too long |
| 422 | Bad input (both or neither of text/url), URL couldn't be scraped, or the AI declined |
| 429 | Rate-limited by the AI service |
| 500 | API key missing/invalid, or the Ollama model isn't downloaded |
| 502 / 503 / 504 | AI service error, malformed output twice, unreachable (e.g. Ollama not running), or timed out |

*AI-generated analysis is for information only. It is not legal advice.*
