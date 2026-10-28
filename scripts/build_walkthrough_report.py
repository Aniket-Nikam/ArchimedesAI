"""Build the illustrated report from observed browser and database evidence."""

import json
import statistics
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/user-study"
OUT = ROOT / "output/pdf/ArchimedesAI_User_Walkthrough_Report.pdf"
W, H = landscape(A4)
NAVY = colors.HexColor("#142c42")
TEAL = colors.HexColor("#007e85")
MUTED = colors.HexColor("#516575")
STYLE = ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=16, textColor=NAVY)


def ascii_text(value):
    for old, new in (
        ("\u2011", "-"),
        ("\u2013", "-"),
        ("\u2014", "-"),
        ("\u2019", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u00a0", " "),
    ):
        value = str(value).replace(old, new)
    return str(value).encode("ascii", "replace").decode()


def paragraph(text, x, top, width, size=11):
    style = ParagraphStyle("p", parent=STYLE, fontSize=size, leading=size * 1.45)
    p = Paragraph(escape(ascii_text(text)).replace("\n", "<br/>"), style)
    _, height = p.wrap(width, H)
    p.drawOn(pdf, x, top - height)
    return top - height - 14


def page(section, title, subtitle=""):
    global number
    if number:
        pdf.showPage()
    number += 1
    pdf.setFillColor(colors.HexColor("#f6f9fb"))
    pdf.rect(0, 0, W, H, fill=1, stroke=0)
    pdf.setFillColor(TEAL)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(38, H - 32, "ARCHIMEDES AI  /  " + section.upper())
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(38, H - 70, ascii_text(title))
    if subtitle:
        paragraph(subtitle, 38, H - 86, W - 76, 10)
    pdf.setStrokeColor(colors.HexColor("#cfdae1"))
    pdf.line(38, 31, W - 38, 31)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(38, 18, "28 OCT 2026  |  LOCAL BROWSER STUDY  |  DEPLOYMENT EXCLUDED")
    pdf.drawRightString(W - 38, 18, f"{number:02d}")


def image(path, top=H - 125, bottom=47):
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    scale = min((W - 76) / iw, (top - bottom) / ih)
    width, height = iw * scale, ih * scale
    pdf.drawImage(reader, (W - width) / 2, top - height, width, height)


def diagram(labels, caption):
    x, y, width, gap = 38, 305, (W - 76 - 36 * (len(labels) - 1)) / len(labels), 36
    for i, label in enumerate(labels):
        left = x + i * (width + gap)
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(TEAL)
        pdf.roundRect(left, y, width, 110, 8, fill=1, stroke=1)
        paragraph(label, left + 12, y + 88, width - 24, 12)
        if i < len(labels) - 1:
            pdf.setStrokeColor(TEAL)
            pdf.line(left + width, y + 55, left + width + gap - 4, y + 55)
            pdf.line(left + width + gap - 10, y + 60, left + width + gap - 4, y + 55)
            pdf.line(left + width + gap - 10, y + 50, left + width + gap - 4, y + 55)
    paragraph(caption, 38, 250, W - 76, 12)


def main():
    global pdf, number
    data = json.loads((STUDY / "results.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    complete = [c for c in cases if c["state"] == "complete"]
    found = sum(c.get("expected_paper_found", False) for c in complete)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(OUT), pagesize=(W, H))
    pdf.setTitle("ArchimedesAI - Real-user research walkthrough and reliability report")
    pdf.setAuthor("ArchimedesAI engineering review")
    number = 0
    page(
        "Evidence report",
        "From question to research evidence",
        "Ten real-paper research scenarios, observed through the normal application interface.",
    )
    y = paragraph("ArchimedesAI\nResearch walkthrough & reliability review", 38, 440, 680, 29)
    y = paragraph(
        f"{len(complete)}/10 reports completed  |  {found}/10 expected titles retrieved in the final observed runs",
        38,
        y - 12,
        740,
        17,
    )
    paragraph(
        "This report documents real live-provider runs, the defects they exposed, the improvements made, and the boundaries of the evidence. It is an engineering review, not an independent security audit or scientific validation certificate.",
        38,
        y - 12,
        700,
        13,
    )
    page("Method", "What was actually tested")
    y = H - 132
    for text in [
        "Research questions were typed into the normal browser form. The app called live scholarly services and the configured Groq model. Screenshots capture the actual interface, not fabricated results.",
        "Ten target titles and review concerns were labelled in cases.json. The read-only collector joins each question to its latest saved report. Earlier failed or superseded attempts remain recorded in results.json; this is not a first-attempt success rate.",
        "An isolated local study account/database kept the walkthrough separate from existing user research. Credentials, session cookies, encrypted keys and full published paper files are excluded from the report and repository.",
        "Automated tests use synthetic providers and a separate database. Their results are reported separately from live retrieval and browser observations.",
        "Claim review is a limited agent-assisted comparison of main ideas with linked original-paper descriptions. It does not measure the accuracy of every sentence, extraction cell, citation or generated manuscript.",
    ]:
        y = paragraph(text, 38, y, W - 76, 12)
    page("Architecture", "How a research request moves")
    diagram(
        [
            "Browser\nCookie session\nQuestion + mode",
            "Durable job\nSQLite state\nWorker process",
            "Evidence\nParallel sources\nCitation metadata",
            "AI + report\nSource IDs\nSaved history",
        ],
        "Progress is streamed from persisted events. A browser disconnect leaves the job running. A stale worker lease can trigger a bounded restart; completion and saved-report insertion happen atomically.",
    )
    page("Lifecycle", "Recovery has explicit boundaries")
    diagram(
        [
            "Queued\nAdmission limits\nPersist request",
            "Running\nGeneration lease\nDeadline monitor",
            "Terminal\nComplete / error\nOr cancellation",
        ],
        "Expired leases are reclaimable up to three attempts within the original deadline. Recovery repeats computation; it does not resume a provider socket. Cancellation terminates the owned worker, but cannot retract requests already received by an external provider.",
    )
    page("Workflow", "Use the result as a starting point")
    diagram(
        [
            "Ask\nName a paper or\nresearch question",
            "Inspect\nSource coverage\nLinked evidence",
            "Organize\nBookmark / notes\nExport metadata",
            "Draft + verify\nMatrix / manuscript\nRead originals",
        ],
        "The paper-search checkbox skips AI synthesis. With it unchecked, the app produces an AI-assisted synthesis. A confidence badge or matched citation identity does not establish that a claim is scientifically correct.",
    )
    page("Live results", "Ten labelled research scenarios")
    y = H - 128
    for c in cases:
        status = "target found" if c.get("expected_paper_found") else "target missing"
        y = paragraph(
            f"{c['id']}  {c['topic']}  |  {c.get('papers', '-')} papers  |  {c.get('elapsed_seconds', '-')}s  |  {status}",
            38,
            y,
            W - 76,
            11,
        )
    times = [c["elapsed_seconds"] for c in complete]
    paragraph(
        f"Final-run server pipeline time: median {statistics.median(times):.1f}s; range {min(times):.1f}-{max(times):.1f}s. Browser rendering and delayed-proxy delivery can take longer. Ten selected questions do not establish general relevance or uptime.",
        38,
        y - 3,
        W - 76,
        10,
    )
    for c in cases:
        page(c["id"], c["topic"], "Observed question, expected evidence and result")
        y = paragraph("QUESTION\n" + c["query"], 38, H - 130, W - 76, 12)
        y = paragraph(
            "EXPECTED PAPER\n" + c["expected_title"] + "\n" + c["reference"], 38, y, W - 76, 11
        )
        y = paragraph(
            f"OBSERVED\n{c.get('papers', 0)} papers; {c.get('elapsed_seconds', '-')} seconds; expected title {'found at rank ' + str(c.get('expected_rank')) if c.get('expected_paper_found') else 'not retrieved in this run'}. {c.get('citation_edges', 0)} retrieved citation links.",
            38,
            y,
            W - 76,
            12,
        )
        y = paragraph("REVIEW FOCUS\n" + c["review_focus"], 38, y, W - 76, 11)
        coverage = "; ".join(
            f"{s['source']}: {s['status']} ({s.get('count', 0)})"
            for s in c.get("source_status", [])
        )
        paragraph("SOURCE COVERAGE\n" + coverage, 38, y, W - 76, 10)
        path = STUDY / "screenshots" / (c["id"] + "-overview.jpg")
        page(
            c["id"] + " / interface",
            "Observed application output",
            c["topic"] + " - actual browser screenshot; original layout preserved",
        )
        image(path)
    page("Citation network", "Papers can exist without retrieved links")
    y = paragraph(
        "The old canvas could render blank even when nodes existed. The replacement uses deterministic SVG positions, visible labels, keyboard-selectable papers and explicit no-link messaging. Only retrieved citation relationships become arrows. Zero links means unavailable or absent relationship data, not that the papers are unrelated.",
        38,
        H - 128,
        W - 76,
        12,
    )
    image(STUDY / "screenshots/UC03-citation-network.jpg", top=y - 4)
    workflows = STUDY / "workflow-observations.json"
    if workflows.exists():
        for workflow in json.loads(workflows.read_text(encoding="utf-8")):
            page("Workflow check", workflow["title"], workflow["result"])
            if workflow.get("screenshot"):
                image(STUDY / workflow["screenshot"])
            else:
                paragraph(workflow["detail"], 38, H - 140, W - 76, 13)
    page("Scientific review", "Useful outputs still need source review")
    y = H - 130
    for text in [
        "Selected main ideas in the eight arXiv cases agree with the original abstract descriptions: attention-based Transformers, bidirectional BERT, retrieval plus generation, residual learning, frozen LoRA weights, neighbourhood attention, hierarchical approximate search and stabilizer-based surface codes.",
        "Completeness is weaker than topic relevance. The BERT overview omits next-sentence prediction. The RAG overview does not fully detail the dense Wikipedia index or sequence/token variants. The CRISPR overview does not fully explain the two RNA components. Ten title hits do not establish ten complete scientific answers.",
        "The CRISPR manuscript blurred RNA roles and PAM recognition and inferred absent study work from short excerpts. The first uploaded-PDF comparison recommended later papers as missing references and treated excerpt omissions as paper omissions. These failures are recorded rather than counted as scientific passes.",
        "Drafting and PDF-comparison prompts now prohibit those unsupported inferences, and the interface labels the outputs provisional. This does not guarantee correctness. A larger labelled dataset and independent domain-expert review remain necessary.",
        "AlphaFold and CRISPR identity was checked with retrieved metadata; publisher full text was not independently inspected through the web tool. See docs/user-study/CLAIM_REVIEW.md for case-by-case checks and the exact scope of source access.",
    ]:
        y = paragraph(text, 38, y, W - 76, 12)
    page("Automated verification", "What the reliability checks establish")
    y = H - 126
    for text in [
        "Backend: 53 tests. Frontend: 7 tests. Lint, type checking and production build are checked separately. Automated provider responses are synthetic and do not contribute to live-paper success metrics.",
        "Persistence: 25,000 saved reports backed up and restored with integrity/hash verification. Eight concurrent writers preserve 400 bookmark records. Additive migrations are rolled back and reapplied without losing existing research.",
        "Failure handling: simulated SQLITE_FULL rolls back safely; database errors return sanitized 503 responses; corrupt backups are rejected. This does not reproduce a physically full disk or every filesystem failure.",
        "Input/security: a seeded corpus of 100 malformed JSON bodies and 100 malformed PDFs produces client errors, plus adversarial usernames, private-path and security-header checks. This is bounded fuzzing, not an independent audit.",
        "Jobs/models: persisted event replay, stale-lease recovery, cross-process rate windows, owned-process cancellation, retired-model filtering, output truncation fallback and title preservation have regression coverage.",
        "Streaming/graph: split UTF-8 and JSON frames, malformed/truncated events, cancellation and finite node layouts are tested. The graph bundle decreased from approximately 194 KB to 8.47 KB after replacing the physics canvas.",
    ]:
        y = paragraph(text, 38, y, W - 76, 11)
    page("Findings", "Failures were part of the evaluation")
    y = H - 130
    for text in [
        "Initial live synthesis failed because the previously configured model identifiers were unavailable. Model discovery now filters configured fallbacks against the provider catalogue; completion length and context are bounded.",
        "A broad Transformer search initially returned related work rather than the original. Preserving explicitly named titles improved retrieval. Biomedical misses exposed limits in keyword and source coverage; direct PubMed and exact-title Crossref lookups were added, and reruns are disclosed.",
        "Provider rate limits occurred during the study. Shared pacing and bounded retries reduce bursts but cannot guarantee access. Source coverage remains visible and metadata failures remain unknown.",
        "An oversized chunked request initially returned 400 because parsing swallowed the size-limit exception. Pre-parser bounded spooling now produces 413. The blank citation canvas was independently fixed rather than explained away as missing links.",
    ]:
        y = paragraph(text, 38, y, W - 76, 12)
    page("Assessment", "How reliable is it now?")
    y = H - 130
    for text in [
        "Suitable for a local research-assistance demonstration: named-paper discovery, source inspection, saved history and interactive evidence exploration are backed by live browser observations and regression tests.",
        "Not yet established: a production availability SLA, broad relevance benchmark, independent penetration audit, expert-labelled scientific accuracy, or exhaustive extraction and manuscript quality. A matched source ID is not proof of entailment.",
        "Retraction status remains incomplete. Crossref and OpenAlex may share upstream metadata, and a missing notice is not evidence of safety. Metadata dates may differ between preprint and journal versions.",
        "Operational limits include one-host SQLite coordination, no automatic job-event retention, bounded retry recovery and unverified real deployment/proxy/storage behavior. Configure retention, backups, monitoring and expert review before production.",
        "Deployment, HTTPS configuration and public hosting were deliberately excluded at the user's request. The repository contains controls and test evidence, not a claim that every external assurance is complete.",
    ]:
        y = paragraph(text, 38, y, W - 76, 12)
    page("Reproduce", "Evidence files and verification commands")
    y = H - 130
    for text in [
        "docs/user-study/cases.json: predefined questions, target titles and review concerns. results.json: latest saved outputs, metadata, provider observations and all job attempts. browser-observations.json: UI-captured synthesis and screenshots.",
        "python scripts/collect_user_study.py reads the isolated study database; it does not initiate research. python scripts/build_walkthrough_report.py generates this PDF from collected evidence.",
        "python -m pytest -q\npython -m ruff check auth api ai db routers services utils main.py tests\npython -m ruff format --check auth api ai db routers services utils main.py tests\ncd frontend: npm test; npm run lint; npm run build",
        "Original-paper references are listed beside each use case. Crossref API reference: https://api.crossref.org/swagger-ui/index.html . Repository: https://github.com/Aniket-Nikam/ArchimedesAI .",
        "Read docs/OPERATIONS_REVIEW.md for backup, cancellation, credential-storage and operating boundaries. Historical automated reports describe earlier revisions and must not be substituted for this live study.",
    ]:
        y = paragraph(text, 38, y, W - 76, 12)
    pdf.save()
    print(f"Created {OUT} ({number} pages)")


if __name__ == "__main__":
    main()
