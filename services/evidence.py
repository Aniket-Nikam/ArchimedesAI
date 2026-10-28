"""Deterministic citation membership checks, separate from model self-review."""

import re


def attach_evidence_ids(papers):
    for index, paper in enumerate(papers, 1):
        paper["evidence_id"] = f"S{index}"
    return papers


def validate_findings(result, papers):
    lookup = {paper.get("evidence_id", f"S{i}"): paper for i, paper in enumerate(papers, 1)}
    titles = {
        re.sub(r"\W", "", str(p.get("title", "")).casefold()): key for key, p in lookup.items()
    }
    unknown = 0
    findings = result.get("key_findings", [])
    if not isinstance(findings, list):
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        values = finding.get("sources", [])
        if not isinstance(values, list):
            values = []
        verified, unmatched = [], []
        for value in values:
            candidate = str(value).strip("[] ")
            key = (
                candidate
                if candidate in lookup
                else titles.get(re.sub(r"\W", "", candidate.casefold()))
            )
            if key and key not in verified:
                verified.append(key)
            elif not key:
                unmatched.append(str(value))
        finding["source_ids"] = verified
        finding["sources"] = [lookup[key]["title"] for key in verified]
        finding["unverified_sources"] = unmatched
        finding["text"] = str(finding.get("text", ""))
        if unmatched or not verified:
            finding["confidence"] = "LOW"
        unknown += len(unmatched)
    result["evidence_review"] = {
        "unmatched_citations": unknown,
        "method": "Exact membership in the retrieved evidence set",
        "limitation": "A matched citation establishes identity, not that the paper supports the claim. Review original sources.",
    }
    return result
