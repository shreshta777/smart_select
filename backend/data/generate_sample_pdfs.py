"""Generates all 18 sample Resume PDFs and 1 Sample JD PDF for real PDF shortlisting."""

import json
from pathlib import Path
import fitz  # PyMuPDF

DATA_DIR = Path(__file__).parent
SAMPLE_PDF_DIR = DATA_DIR / "sample_pdfs"
SAMPLE_PDF_DIR.mkdir(parents=True, exist_ok=True)


def create_pdf(file_path: Path, title: str, sections_dict: dict):
    """Creates a formatted multi-section PDF document using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    y = 50
    # Header / Title
    page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 26

    for heading, content in sections_dict.items():
        if y > 740:
            page = doc.new_page(width=595, height=842)
            y = 50

        # Section Heading
        page.insert_text((50, y), heading.upper(), fontsize=11, fontname="helv", color=(0.2, 0.2, 0.2))
        y += 16

        # Section Body
        if isinstance(content, list):
            for item in content:
                if y > 760:
                    page = doc.new_page(width=595, height=842)
                    y = 50
                page.insert_text((60, y), f"- {item}", fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
                y += 14
            y += 8
        else:
            lines = str(content).split("\n")
            for line in lines:
                if y > 760:
                    page = doc.new_page(width=595, height=842)
                    y = 50
                page.insert_text((50, y), line, fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
                y += 14
            y += 8

    doc.save(str(file_path))
    doc.close()
    print(f"Generated PDF: {file_path.name}")


def generate_all_sample_pdfs():
    # 1. Generate Sample JD PDF
    jd_json_path = DATA_DIR / "dummy_jd.json"
    with open(jd_json_path, "r", encoding="utf-8") as f:
        jd_data = json.load(f)

    jd_sections = {
        "Job Title": f"{jd_data.get('job_title', 'Developer Intern')} - {jd_data.get('company', 'TechNova Solutions')}",
        "Overview": jd_data.get("description", ""),
        "Required Skills": jd_data.get("required_skills", []),
        "Preferred Skills": jd_data.get("preferred_skills", []),
        "Key Responsibilities": jd_data.get("responsibilities", []),
        "Education Requirements": jd_data.get("education_requirements", []),
        "Experience Requirements": jd_data.get("experience_requirements", [])
    }
    create_pdf(SAMPLE_PDF_DIR / "Sample_JD.pdf", f"{jd_data.get('company', 'TechNova')} - Job Description", jd_sections)

    # 2. Generate All 18 Resume PDFs from dummy_resumes.json
    resumes_json_path = DATA_DIR / "dummy_resumes.json"
    with open(resumes_json_path, "r", encoding="utf-8") as f:
        resumes_data = json.load(f)

    for idx, r in enumerate(resumes_data, start=1):
        name_slug = r["name"].replace(" ", "_")
        filename = f"Resume_{idx:02d}_{name_slug}.pdf"
        r_sections = {
            "Candidate Information": f"{r['name']}\nEmail: {r['name'].lower().replace(' ', '.')}@example.com | Candidate ID: {r['candidate_id']}",
            "Technical Skills": [", ".join(r.get("skills", []))],
            "Work Experience": r.get("experience", []),
            "Key Projects": r.get("projects", []),
            "Education": r.get("education", []),
            "Certifications": r.get("certifications", [])
        }
        create_pdf(SAMPLE_PDF_DIR / filename, f"{r['name']} - Curriculum Vitae", r_sections)


if __name__ == "__main__":
    generate_all_sample_pdfs()
