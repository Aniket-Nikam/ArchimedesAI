from types import SimpleNamespace as NS

from ai import groq_service
from services.search_intent import named_title, title_score


def test_retired_models_are_filtered(monkeypatch):
    monkeypatch.setattr(groq_service.config, "FALLBACK_MODELS", ["retired", "available"])
    monkeypatch.setattr(
        groq_service, "groq_client", NS(models=NS(list=lambda: NS(data=[NS(id="available")])))
    )
    groq_service._models.cache_clear()
    try:
        assert groq_service._models() == ["available"]
    finally:
        groq_service._models.cache_clear()


def test_truncated_completion_falls_back_with_bounded_context(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return NS(
            choices=[
                NS(
                    finish_reason="length" if len(calls) == 1 else "stop",
                    message=NS(content='{"ok":true}'),
                )
            ]
        )

    monkeypatch.setattr(groq_service, "groq_client", NS(chat=NS(completions=NS(create=create))))
    monkeypatch.setattr(groq_service, "_models", lambda: ["first", "second"])
    assert groq_service._call_llm("Return a JSON object", "x" * 20000) == '{"ok":true}'
    assert [call["model"] for call in calls] == ["first", "second"]
    assert all(len(call["messages"][1]["content"]) == 14000 for call in calls)
    assert all(call["max_completion_tokens"] == 3000 for call in calls)


def test_named_paper_survives_query_extraction():
    title = named_title('Find "Attention Is All You Need" and explain attention.')
    assert title == "Attention Is All You Need"
    assert title_score({"title": title}, title) > title_score(
        {"title": "Related attention work"}, title
    )


def test_crossref_rejects_similar_but_different_titles(monkeypatch):
    from api import crossref_client

    monkeypatch.setattr(
        crossref_client,
        "resilient_request",
        lambda *a, **k: NS(
            status_code=200,
            json=lambda: {
                "message": {
                    "items": [
                        {
                            "title": ["Requested paper."],
                            "DOI": "10.test/original",
                            "abstract": "<jats:p>Evidence</jats:p>",
                        },
                        {"title": ["Requested paper commentary"], "DOI": "10.test/other"},
                    ]
                }
            },
        ),
    )
    papers = crossref_client.search_crossref_title("Requested paper")
    assert len(papers) == 1
    assert papers[0]["doi"] == "10.test/original"
    assert papers[0]["abstract"] == "Evidence"
