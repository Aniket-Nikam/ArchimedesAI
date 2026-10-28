"""Stable deduplication across scholarly providers."""

import re


def unique_papers(papers, seen=None):
    seen = seen if seen is not None else set()
    result = []
    for paper in papers:
        title = re.sub(r"[^\w]", "", str(paper.get("title", "")).casefold())
        doi = str(paper.get("doi") or "").lower().removeprefix("https://doi.org/")
        keys = {f"title:{title}"} if title else set()
        if doi:
            keys.add(f"doi:{doi}")
        if not keys or keys & seen:
            continue
        seen.update(keys)
        result.append(paper)
    return result
