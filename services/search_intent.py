"""Keep explicitly named paper titles intact instead of reducing them to keywords."""

import re


def named_title(query):
    quoted = re.search(r'["“](.{5,220}?)["”]', query)
    if quoted:
        return quoted.group(1)
    match = re.match(
        r"(?i)\s*(?:find|locate)\s+(.{5,220}?)\s+and\s+(?:explain|summarize|describe|compare)\b",
        query,
    )
    return match.group(1).strip(" .") if match else None


def title_score(paper, title):
    def normalize(value):
        return re.sub(r"\W", "", value.casefold())

    actual = normalize(str(paper.get("title", "")))
    expected = normalize(title or "")
    return 2 if expected and actual == expected else 1 if expected and expected in actual else 0
