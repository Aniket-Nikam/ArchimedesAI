from ai.groq_service import _build_paper_text, _call_llm


def generate_manuscript_draft(section, notes, papers):
    """
    Generates a draft of a manuscript section (Introduction, Discussion, etc.)
    using the provided notes and injecting citations from the provided papers.
    """
    if not papers:
        paper_text = "No papers provided. Do not include citations."
    else:
        paper_text = _build_paper_text(papers, max_papers=20)

    system_prompt = f"""You are an expert academic writer and researcher. Your task is to draft the {section} section of a scientific manuscript.

You will be provided with:
1. The user's rough notes, experimental results, or bullet points.
2. A list of reference papers (with abstracts and years).

RULES:
1. Write a provisional {section} section grounded in the supplied evidence. User notes are unverified suggestions, not experimental evidence.
2. You MUST inject in-text APA citations (e.g., Smith et al., 2023) where appropriate to support the claims, using ONLY the reference papers provided.
3. Omit unsupported factual claims. Mark a gap as "Not stated in the supplied excerpts"; do not infer that the original study did not investigate something merely because its abstract omits it. Do not add mechanisms or numerical results from general knowledge.
4. Structure the text logically with paragraphs.
5. Use markdown formatting. Include a "References" section at the end listing the full citations of the papers you actually used in the text.

Output ONLY the markdown text of the draft."""

    result = _call_llm(system_prompt, f"USER'S NOTES:\n{notes}\n\nREFERENCE PAPERS:\n{paper_text}")
    return result or "Failed to generate manuscript draft."
