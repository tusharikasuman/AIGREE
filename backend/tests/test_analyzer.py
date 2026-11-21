"""Offline tests: a fake Claude client stands in for the API, so no key or network is needed."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import config
from app.analyzer import AnalysisError, Analyzer, dedupe_clauses
from app.chunker import chunk_text
from app.main import app
from app.schemas import FlaggedClause

SAMPLE = (Path(__file__).resolve().parent.parent / "samples" / "sample_tos.txt").read_text(encoding="utf-8")
ARBITRATION = "Any dispute arising out of or relating to these Terms or the Service will be resolved by final and binding individual arbitration, and not in court."
NO_REFUNDS = "All payments are non-refundable"


def good_json(**overrides) -> str:
    data = {
        "summary": "Strict terms with auto-renewal and arbitration.",
        "trust_score": 30,
        "sub_scores": {"data_privacy": 20, "financial_risk": 30, "user_rights": 25, "exit_clauses": 20},
        "flagged_clauses": [
            {"category": "Dispute Resolution", "severity": "high", "original_text": ARBITRATION,
             "explanation": "You can't sue them in court."},
            {"category": "Financial", "severity": "medium", "original_text": NO_REFUNDS,
             "explanation": "You won't get money back."},
        ],
    }
    data.update(overrides)
    return json.dumps(data)


def reply(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class FakeMessages:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        r = self.replies.pop(0)
        return r(kwargs) if callable(r) else r


class FakeClient:
    def __init__(self, replies):
        self.messages = FakeMessages(replies)
        self.beta = SimpleNamespace(messages=self.messages)


@pytest.mark.asyncio
async def test_single_chunk_happy_path():
    client = FakeClient([reply(good_json())])
    result = await Analyzer(client).analyze(SAMPLE)
    assert result.trust_score == 30
    assert [c.severity for c in result.flagged_clauses] == ["high", "medium"]
    call = client.messages.calls[0]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "<document>" in call["messages"][0]["content"]


@pytest.mark.asyncio
async def test_retries_once_on_malformed_json():
    client = FakeClient([reply('{"summary": "oops"'), reply(good_json())])
    result = await Analyzer(client).analyze(SAMPLE)
    assert result.trust_score == 30
    retry_msgs = client.messages.calls[1]["messages"]
    assert retry_msgs[1]["role"] == "assistant"
    assert "failed validation" in retry_msgs[2]["content"]


@pytest.mark.asyncio
async def test_retries_on_out_of_range_score_then_succeeds():
    client = FakeClient([reply(good_json(trust_score=140)), reply(good_json())])
    result = await Analyzer(client).analyze(SAMPLE)
    assert result.trust_score == 30
    assert "trust_score" in client.messages.calls[1]["messages"][2]["content"]


@pytest.mark.asyncio
async def test_gives_up_after_second_failure():
    client = FakeClient([reply("not json"), reply("still not json")])
    with pytest.raises(AnalysisError, match="malformed output twice"):
        await Analyzer(client).analyze(SAMPLE)
    assert len(client.messages.calls) == 2


@pytest.mark.asyncio
async def test_summary_over_150_words_triggers_retry():
    client = FakeClient([reply(good_json(summary="word " * 151)), reply(good_json())])
    result = await Analyzer(client).analyze(SAMPLE)
    assert len(result.summary.split()) < 150


@pytest.mark.asyncio
async def test_drops_hallucinated_quotes():
    data = json.loads(good_json())
    data["flagged_clauses"].append({"category": "Other", "severity": "high",
                                    "original_text": "We own your firstborn child.", "explanation": "x"})
    client = FakeClient([reply(json.dumps(data))])
    result = await Analyzer(client).analyze(SAMPLE)
    assert all("firstborn" not in c.original_text for c in result.flagged_clauses)
    assert len(result.flagged_clauses) == 2


@pytest.mark.asyncio
async def test_refusal_is_reported():
    client = FakeClient([reply("", stop_reason="refusal")])
    with pytest.raises(AnalysisError) as e:
        await Analyzer(client).analyze(SAMPLE)
    assert e.value.status_code == 422


@pytest.mark.asyncio
async def test_long_document_is_chunked_and_merged(monkeypatch):
    monkeypatch.setattr(config, "CHUNK_CHARS", 2000)
    n_chunks = len(chunk_text(SAMPLE.strip(), 2000, config.CHUNK_OVERLAP_CHARS))
    assert n_chunks > 1

    def chunk_reply(kwargs):
        if "part_analyses" in kwargs["messages"][0]["content"]:
            return reply(json.dumps({"summary": "Merged.", "trust_score": 22, "sub_scores":
                                     {"data_privacy": 15, "financial_risk": 25, "user_rights": 20, "exit_clauses": 18}}))
        content = kwargs["messages"][0]["content"]
        clauses = [c for c in json.loads(good_json())["flagged_clauses"] if c["original_text"] in content]
        return reply(good_json(flagged_clauses=clauses))

    client = FakeClient([chunk_reply] * (n_chunks + 1))
    result = await Analyzer(client).analyze(SAMPLE)
    assert len(client.messages.calls) == n_chunks + 1
    assert result.summary == "Merged." and result.trust_score == 22
    assert {c.original_text for c in result.flagged_clauses} == {ARBITRATION, NO_REFUNDS}


def test_dedupe_keeps_more_severe_and_drops_contained_duplicates():
    a = FlaggedClause(category="Financial", severity="low", original_text="All payments are non-refundable", explanation="x")
    b = FlaggedClause(category="Financial", severity="high",
                      original_text="All payments are non-refundable, including for partially used billing periods", explanation="y")
    out = dedupe_clauses([a, b])
    assert out == [b]


def test_chunker_respects_size_and_covers_text():
    chunks = chunk_text(SAMPLE.strip(), 1500, 200)
    assert all(len(c) <= 1500 for c in chunks)
    assert chunks[0].startswith("StreamNest Terms") and chunks[-1].endswith("legal@streamnest.example.")


def test_api_validation_and_happy_path():
    client = TestClient(app)
    assert client.post("/analyze", json={}).status_code == 422
    assert client.post("/analyze", json={"text": "x" * 300, "url": "https://a.com"}).status_code == 422

    app.state.analyzer = Analyzer(FakeClient([reply(good_json())]))
    r = client.post("/analyze", json={"text": SAMPLE})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"summary", "trust_score", "sub_scores", "flagged_clauses"}
    assert set(body["sub_scores"]) == {"data_privacy", "financial_risk", "user_rights", "exit_clauses"}

    app.state.analyzer = Analyzer(FakeClient([]))
    assert client.post("/analyze", json={"text": "too short"}).status_code == 400
    app.state.analyzer = None
