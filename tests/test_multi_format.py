"""Multi-format parsing and integration tests for PDF, DOCX, TXT, and HTML documents."""

import io
import fitz
import docx
from fastapi.testclient import TestClient

from backend.main import app
from backend.parser import (
    parse_pdf,
    parse_docx,
    parse_txt,
    parse_html,
    detect_file_format,
    extract_text_from_file,
    parse_resume,
    parse_job_description,
)


def create_in_memory_pdf(text: str) -> bytes:
    """Helper to generate a valid in-memory PDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def create_in_memory_docx(paragraphs: list, table_data: list = None) -> bytes:
    """Helper to generate a valid in-memory DOCX file."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table_data:
        table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
        for r_idx, row in enumerate(table_data):
            for c_idx, cell_value in enumerate(row):
                table.rows[r_idx].cells[c_idx].text = cell_value
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


# =========================================================================
# UNIT TESTS: INDIVIDUAL EXTRACTORS
# =========================================================================

def test_parse_docx_extractor():
    paragraphs = [
        "Elena Rostova",
        "elena@example.com",
        "Technical Skills:",
        "Python, Django, React, AWS, Docker, PostgreSQL",
        "Work Experience:",
        "- Full Stack Developer at WebForge: Built microservices using Python and Django.",
        "- Designed reactive frontends with React.",
        "Education:",
        "- B.S. in Software Engineering",
    ]
    docx_bytes = create_in_memory_docx(paragraphs)
    text = parse_docx(docx_bytes)
    assert "Elena Rostova" in text
    assert "Python" in text
    assert "Django" in text
    assert "Full Stack Developer" in text


def test_parse_html_extractor():
    html_markup = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Resume - Marcus Aurelius</title>
        <style>body { font-family: sans-serif; }</style>
        <script>console.log("malicious script");</script>
      </head>
      <body>
        <h1>Marcus Aurelius</h1>
        <div class="contact">marcus@example.com | 555-0199</div>
        <h2>Technical Skills</h2>
        <p>JavaScript, Node.js, React, MongoDB, Express, GraphQL</p>
        <h2>Experience</h2>
        <ul>
          <li>Senior Backend Engineer: Scaled Node.js APIs to 100k RPM.</li>
          <li>Implemented MongoDB indexing strategies.</li>
        </ul>
        <h2>Education</h2>
        <p>M.S. in Computer Science</p>
      </body>
    </html>
    """
    text = parse_html(html_markup)
    assert "Marcus Aurelius" in text
    assert "JavaScript" in text
    assert "Node.js" in text
    assert "malicious script" not in text
    assert "<style>" not in text
    assert "Scaled Node.js APIs" in text


def test_parse_txt_extractor():
    txt_content = (
        "Sarah Jenkins\n"
        "sarah@example.com\n\n"
        "Technical Skills:\n"
        "React, Node.js, TypeScript, REST APIs, PostgreSQL\n\n"
        "Experience:\n"
        "- Frontend Developer at PixelSoft: Created reusable UI components.\n\n"
        "Education:\n"
        "- B.Sc in Information Technology\n"
    )
    text = parse_txt(txt_content.encode("utf-8"))
    assert "Sarah Jenkins" in text
    assert "TypeScript" in text
    assert "Reusable UI components" in text or "reusable UI components" in text


def test_detect_file_format():
    pdf_bytes = create_in_memory_pdf("Sample PDF content")
    assert detect_file_format(pdf_bytes, "test.pdf") == "pdf"

    docx_bytes = create_in_memory_docx(["Sample Docx content"])
    assert detect_file_format(docx_bytes, "test.docx") == "docx"

    html_bytes = b"<!DOCTYPE html><html><body><h1>Test</h1></body></html>"
    assert detect_file_format(html_bytes, "test.html") == "html"

    txt_bytes = b"Just plain text without markup"
    assert detect_file_format(txt_bytes, "test.txt") == "txt"


# =========================================================================
# INTEGRATION TESTS: FASTAPI MULTI-FORMAT ENDPOINTS
# =========================================================================

client = TestClient(app)

SAMPLE_JD_TEXT = """
TechNova Solutions
Junior Full Stack Developer Intern

Required Skills:
- JavaScript
- React
- Node.js
- MongoDB
- REST APIs

Preferred Skills:
- Docker
- AWS

Key Responsibilities:
- Build responsive web applications using React.
- Develop scalable backend RESTful APIs using Node.js and MongoDB.
"""

SAMPLE_RESUME_A_TEXT = """
Alex Vance
alex.vance@example.com

Technical Skills:
JavaScript, React, Node.js, MongoDB, REST APIs, Docker, AWS

Work Experience:
- Full Stack Intern: Developed Node.js REST APIs and responsive React dashboards.
- Deployed microservices using Docker on AWS.

Education:
- B.Tech in Computer Science
"""

SAMPLE_RESUME_B_TEXT = """
Sarah Chen
sarah.chen@example.com

Technical Skills:
JavaScript, React, Node.js, REST APIs, HTML5, CSS3

Work Experience:
- Frontend Engineer Intern: Built modern web apps with React.
- Integrated REST APIs with backend services.

Education:
- B.S. in Information Systems
"""


def test_end_to_end_docx_pipeline():
    """Tests shortlisting with DOCX Job Description + DOCX Resumes."""
    jd_docx = create_in_memory_docx(SAMPLE_JD_TEXT.split("\n"))
    res_a_docx = create_in_memory_docx(SAMPLE_RESUME_A_TEXT.split("\n"))
    res_b_docx = create_in_memory_docx(SAMPLE_RESUME_B_TEXT.split("\n"))

    response = client.post(
        "/rank",
        files=[
            ("jd_file", ("jd.docx", jd_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("resume_files", ("candidate_a.docx", res_a_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("resume_files", ("candidate_b.docx", res_b_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
        data={"keyword_weight": "0.5", "semantic_weight": "0.5"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_candidates"] == 2
    assert len(data["rankings"]) == 2
    assert data["rankings"][0]["evaluation"]["final_score"] >= data["rankings"][1]["evaluation"]["final_score"]
    assert "Alex Vance" in [r["evaluation"]["name"] for r in data["rankings"]]


def test_end_to_end_html_pipeline():
    """Tests shortlisting with HTML Job Description + HTML Resumes."""
    jd_html = f"<html><body><pre>{SAMPLE_JD_TEXT}</pre></body></html>".encode("utf-8")
    res_a_html = f"<html><body><h1>Alex Vance</h1><p>Technical Skills: JavaScript, React, Node.js, MongoDB, REST APIs, Docker, AWS</p><p>Experience: Built REST APIs with Node.js.</p></body></html>".encode("utf-8")

    response = client.post(
        "/rank",
        files=[
            ("jd_file", ("job_description.html", jd_html, "text/html")),
            ("resume_files", ("alex_vance.html", res_a_html, "text/html")),
        ],
        data={"keyword_weight": "0.5", "semantic_weight": "0.5"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rankings"][0]["evaluation"]["keyword_score"] > 30.0
    assert len(data["rankings"][0]["evaluation"]["matched_required_skills"]) >= 4


def test_end_to_end_mixed_formats_batch():
    """Tests mixed format ingestion in a single batch:
    JD in PDF + Resumes in (1) PDF, (2) DOCX, (3) TXT, (4) HTML.
    """
    jd_pdf = create_in_memory_pdf(SAMPLE_JD_TEXT)
    res_1_pdf = create_in_memory_pdf(SAMPLE_RESUME_A_TEXT)
    res_2_docx = create_in_memory_docx(SAMPLE_RESUME_B_TEXT.split("\n"))
    res_3_txt = (
        "Charlie Zhang\n"
        "charlie@example.com\n\n"
        "Technical Skills:\n"
        "Python, Django, C++, Linux, Docker\n\n"
        "Experience:\n"
        "- Backend Developer: Maintained Django monolith.\n"
    ).encode("utf-8")
    res_4_html = (
        "<html><body>"
        "<h1>David Kim</h1>"
        "<h2>Technical Skills</h2>"
        "<p>JavaScript, React, Node.js, MongoDB, REST APIs, AWS</p>"
        "<h2>Experience</h2>"
        "<p>- Full Stack Engineer: Built full stack JavaScript applications.</p>"
        "</body></html>"
    ).encode("utf-8")

    response = client.post(
        "/rank",
        files=[
            ("jd_file", ("JD.pdf", jd_pdf, "application/pdf")),
            ("resume_files", ("Resume_01.pdf", res_1_pdf, "application/pdf")),
            ("resume_files", ("Resume_02.docx", res_2_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("resume_files", ("Resume_03.txt", res_3_txt, "text/plain")),
            ("resume_files", ("Resume_04.html", res_4_html, "text/html")),
        ],
        data={"keyword_weight": "0.5", "semantic_weight": "0.5"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_candidates"] == 4
    assert len(data["rankings"]) == 4

    # Validate ranks are descending strictly
    scores = [r["evaluation"]["final_score"] for r in data["rankings"]]
    assert scores == sorted(scores, reverse=True)
    assert len(data["top_3_explanations"]) == 3

