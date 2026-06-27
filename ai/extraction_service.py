import json
from ai.groq_service import _call_llm, _parse_json_response

def extract_paper_data(papers):
    if not papers:
        return []
    papers_to_process = papers[:15]
    paper_text = ""
    for idx, p in enumerate(papers_to_process):
        title = p.get('title', 'Unknown Title')
        year = p.get('year', 'N/A')
        abstract = str(p.get('abstract', ''))[:1000]
        paper_text += f"[{idx+1}] Title: {title} ({year})\nAbstract: {abstract}\n\n"

    system_prompt = '''You are a rigorous academic data extraction bot. Your job is to extract methodology and statistical data from the provided papers.
You MUST return a JSON array of objects, one for each paper, matching the exact order provided.

Format each object as:
{
  "title": "Paper Title",
  "methodology": "e.g., Randomized Controlled Trial, Meta-Analysis, Transformer Architecture, etc.",
  "sample_size": "e.g., N=400, or N/A if not applicable",
  "key_metric": "e.g., p < 0.05, accuracy=94%, or main quantitative result",
  "limitations": "Brief summary of limitations"
}

If a field is not explicitly stated or cannot be inferred with high confidence from the abstract, use "Not stated".
Return ONLY the JSON array.'''

    result = _call_llm(system_prompt, f"Papers:\n{paper_text}")
    parsed = _parse_json_response(result)
    
    if isinstance(parsed, list):
        return parsed
    elif isinstance(parsed, dict) and "papers" in parsed:
        return parsed["papers"]
    
    return []
