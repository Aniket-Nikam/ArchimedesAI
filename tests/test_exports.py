import csv
import io

from conftest import register

from services.history_service import save_research_session
from utils.citation_generator import generate_bibtex, generate_csv, generate_ris


def test_export_quotes_and_formula_text():
    paper = {
        "title": '=HYPERLINK("example")',
        "authors": ["A, Author"],
        "abstract": 'Line one, "quoted"\nLine two',
    }
    rows = list(csv.reader(io.StringIO(generate_csv([paper]))))
    assert len(rows) == 2 and len(rows[1]) == 6
    assert rows[1][0].startswith("'=")
    assert rows[1][-1] == paper["abstract"]


def test_bibtex_keys_are_unique_and_ris_fields_cannot_inject_lines():
    papers = [{"title": "Title {braces} & details", "year": 2024, "authors": ["A Smith"]}] * 2
    assert "@article{paper1_2024" in generate_bibtex(papers)
    assert "@article{paper2_2024" in generate_bibtex(papers)
    assert r"\{braces\}" in generate_bibtex(papers)
    assert "\nER  - INJECT" not in generate_ris([{"title": "Title\nER  - INJECT"}])


def test_all_saved_report_export_formats(client):
    user = register(client)
    session_id = save_research_session(
        user["id"], "test", {"seminal": [{"title": "Paper", "authors": ["A Author"]}]}
    )
    for format in ("csv", "bibtex", "apa", "ris"):
        response = client.post("/api/export/", json={"session_id": session_id, "format": format})
        assert response.status_code == 200
        assert "attachment;" in response.headers["content-disposition"]
        assert "Paper" in response.text


def test_auth_endpoints_rate_limit(client):
    for _ in range(30):
        response = client.post("/api/auth/login", json={"username": "absent", "password": "bad"})
        assert response.status_code == 401
    assert (
        client.post("/api/auth/login", json={"username": "absent", "password": "bad"}).status_code
        == 429
    )
