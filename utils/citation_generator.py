"""Citation downloads share one implementation across the API and UI."""

import csv
import io
import re


def _text(value):
    return " ".join(str(value or "").split())


def _authors(paper):
    authors = paper.get("authors")
    return [_text(a) for a in authors if a] if isinstance(authors, list) else []


def generate_apa(paper):
    authors = _authors(paper)
    author = " & ".join(authors) if len(authors) <= 2 else f"{authors[0]} et al."
    return f"{author or 'Unknown Author'} ({_text(paper.get('year')) or 'n.d.'}). {_text(paper.get('title'))}. {_text(paper.get('source'))}."


def _bib(value):
    return (
        _text(value)
        .replace("\\", r"\textbackslash{}")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
        .replace("$", r"\$")
    )


def generate_bibtex(papers):
    entries = []
    for i, paper in enumerate(papers):
        key = re.sub(r"[^a-zA-Z0-9]", "", _text(paper.get("year"))) or "nd"
        fields = {
            "title": paper.get("title"),
            "author": " and ".join(_authors(paper)) or "Unknown",
            "year": paper.get("year"),
            "url": paper.get("url"),
            "doi": paper.get("doi"),
        }
        body = ",\n".join(f"  {name}={{{_bib(value)}}}" for name, value in fields.items() if value)
        entries.append(f"@article{{paper{i + 1}_{key},\n{body}\n}}")
    return "\n\n".join(entries) + "\n"


def _csv_cell(value):
    text = str(value if value is not None else "")
    # Opening the download in a spreadsheet must not execute a paper title.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def generate_csv(papers):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Title", "Authors", "Year", "Source", "Citations", "Abstract"])
    for paper in papers:
        writer.writerow(
            [
                _csv_cell(v)
                for v in (
                    paper.get("title"),
                    "; ".join(_authors(paper)),
                    paper.get("year"),
                    paper.get("source"),
                    paper.get("citations", 0),
                    paper.get("abstract"),
                )
            ]
        )
    return output.getvalue()


def generate_ris(papers):
    entries = []
    for paper in papers:
        lines = ["TY  - JOUR", f"TI  - {_text(paper.get('title'))}"]
        lines.extend(f"AU  - {author}" for author in _authors(paper))
        for field, key in (("PY", "year"), ("UR", "url"), ("DO", "doi"), ("AB", "abstract")):
            if paper.get(key):
                lines.append(f"{field}  - {_text(paper[key])}")
        entries.append("\n".join(lines + ["ER  - "]))
    return "\n\n".join(entries) + "\n"
