"""Integration test specifically verifying genuine PDF parsing from physical PDF files."""

from pathlib import Path
import fitz  # PyMuPDF
from fastapi.testclient import TestClient

from backend.main import app
from backend.parser import parse_pdf, parse_resume, parse_job_description
from backend.models import Resume, JobDescription
from backend.cleaner import clean_text

PDF_DIR = Path(__file__).parent.parent / "backend" / "data" / "sample_pdfs"


def test_physical_pdf_opening_and_text_extraction():
    """Verify that PyMuPDF opens actual .pdf files, iterates pages, and extracts clean text."""
    jd_pdf_path = PDF_DIR / "Sample_JD.pdf"
    assert jd_pdf_path.exists(), f"Missing test PDF at {jd_pdf_path}"

    # 1. Open with fitz directly to inspect low-level page text
    doc = fitz.open(str(jd_pdf_path))
    assert doc.page_count >= 1
    raw_page_texts = [page.get_text() for page in doc]
    doc.close()

    combined_text = "\n".join(raw_page_texts)
    print("\n--- EXTRACTED RAW TEXT FROM Sample_JD.pdf ---")
    print(combined_text)
    print("---------------------------------------------")

    assert "technova solutions" in combined_text.lower()
    assert "required skills" in combined_text.lower()
    assert "mongodb" in combined_text.lower()


def test_parse_resume_from_physical_pdf():
    """Verify resume parsing, section segmentation, and structured model generation from real PDF."""
    resume_path = PDF_DIR / "Resume_01_Aarav_Sharma.pdf"
    assert resume_path.exists()

    # Parse using backend parser
    resume = parse_resume(str(resume_path), candidate_id="C01", filename="Resume_01_Aarav_Sharma.pdf")

    print(f"\n--- PARSED RESUME OBJECT FROM {resume_path.name} ---")
    print(f"Candidate ID: {resume.candidate_id}")
    print(f"Candidate Name: {resume.name}")
    print(f"Skills Extracted ({len(resume.skills)}): {resume.skills}")
    print(f"Experience Items ({len(resume.experience)}): {resume.experience}")
    print(f"Projects Items ({len(resume.projects)}): {resume.projects}")
    print(f"Education: {resume.education}")
    print("-----------------------------------------------------")

    assert isinstance(resume, Resume)
    assert "Aarav Sharma" in resume.name or "Aarav" in resume.raw_text
    assert len(resume.skills) > 0
    assert any("react" in s.lower() or "javascript" in s.lower() for s in resume.skills)
    assert len(resume.experience) > 0
    assert len(resume.projects) > 0


def test_parse_job_description_from_physical_pdf():
    """Verify Job Description parsing and section detection from real PDF."""
    jd_path = PDF_DIR / "Sample_JD.pdf"
    assert jd_path.exists()

    jd = parse_job_description(str(jd_path))

    print(f"\n--- PARSED JOB DESCRIPTION FROM {jd_path.name} ---")
    print(f"Job Title: {jd.job_title}")
    print(f"Required Skills ({len(jd.required_skills)}): {jd.required_skills}")
    print(f"Preferred Skills ({len(jd.preferred_skills)}): {jd.preferred_skills}")
    print(f"Responsibilities ({len(jd.responsibilities)}): {jd.responsibilities}")
    print("--------------------------------------------------")

    assert isinstance(jd, JobDescription)
    assert any("react" in s.lower() or "javascript" in s.lower() for s in jd.required_skills)
    assert any("docker" in s.lower() or "aws" in s.lower() for s in jd.preferred_skills)
    assert len(jd.responsibilities) > 0


def test_end_to_end_full_18_pdf_batch_upload():
    """Verify that uploading the full batch of 18 physical Resume PDFs + 1 JD PDF:
    1. Parses all 18 PDFs with PyMuPDF
    2. Runs matching & scoring
    3. Produces a full 1 to 18 ranked list with top-3 explanations.
    """
    client = TestClient(app)

    jd_path = PDF_DIR / "Sample_JD.pdf"
    assert jd_path.exists()

    resume_pdf_files = sorted(list(PDF_DIR.glob("Resume_*.pdf")))
    assert len(resume_pdf_files) == 18, f"Expected 18 resume PDFs, found {len(resume_pdf_files)}"

    # Open all file handles
    file_handles = []
    files_payload = []

    f_jd = open(jd_path, "rb")
    file_handles.append(f_jd)
    files_payload.append(("jd_file", ("Sample_JD.pdf", f_jd, "application/pdf")))

    for r_path in resume_pdf_files:
        f_r = open(r_path, "rb")
        file_handles.append(f_r)
        files_payload.append(("resume_files", (r_path.name, f_r, "application/pdf")))

    try:
        response = client.post("/rank", files=files_payload)
    finally:
        for fh in file_handles:
            fh.close()

    assert response.status_code == 200, f"Full batch ranking failed: {response.text}"
    result = response.json()

    print(f"\n=======================================================")
    print(f"FULL 18-RESUME BATCH SHORTLISTING RESULT FROM REAL PDFS")
    print(f"Job Title: {result['job_title']}")
    print(f"Total Candidates Processed: {result['total_candidates']}")
    print(f"=======================================================")
    for item in result["rankings"]:
        ev = item["evaluation"]
        print(f"Rank #{item['rank']:02d} | {ev['name']:<20} ({ev['candidate_id']}) | Score: {ev['final_score']:5.1f} | KW: {ev['keyword_score']:5.1f}% | Sem: {ev['semantic_score']:5.1f}%")
    print(f"=======================================================")

    assert result["total_candidates"] == 18
    assert len(result["rankings"]) == 18
    assert len(result["top_3_explanations"]) == 3

    # Check rank order is strictly descending
    for i in range(17):
        assert result["rankings"][i]["evaluation"]["final_score"] >= result["rankings"][i + 1]["evaluation"]["final_score"]


def test_missing_files_validation_error():
    """Verify that calling /rank without uploading required PDF files returns a 400 Bad Request."""
    client = TestClient(app)
    response = client.post("/rank")
    assert response.status_code == 400
    assert "Missing Job Description" in response.json()["detail"] or "No Resume PDFs" in response.json()["detail"]

