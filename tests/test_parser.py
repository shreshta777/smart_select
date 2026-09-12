"""Tests for PDF parsing, text cleaning, and section extraction."""

import io
import fitz
from backend.cleaner import clean_text, extract_bullet_points
from backend.parser import detect_sections, parse_resume, parse_job_description, parse_pdf


def test_clean_text_normalizes_bullets_and_whitespace():
    raw = "• Item 1\r\n\r\n\r\n\r\nPage 1 of 3\n• Item 2  with   spaces\n- Page 1 -"
    cleaned = clean_text(raw)
    assert "Page 1 of 3" not in cleaned
    assert "- Item 1" in cleaned
    assert "- Item 2 with spaces" in cleaned


def test_clean_text_preserves_technical_terms():
    raw = "Experience with Node.js, React.js, C++, and MongoDB in production."
    cleaned = clean_text(raw)
    assert "Node.js" in cleaned
    assert "React.js" in cleaned
    assert "C++" in cleaned
    assert "MongoDB" in cleaned


def test_extract_sections_and_resume_parsing():
    sample_resume_text = """
    Aarav Sharma
    aarav@example.com

    Technical Skills:
    JavaScript, React, Node.js, MongoDB, REST APIs, Docker, AWS

    Work Experience:
    - Software Engineering Intern at CloudScale: Developed RESTful APIs using Node.js.
    - Built frontend dashboards using React.

    Projects:
    - E-Commerce Platform with React and Node.js backend.

    Education:
    - B.Tech in Computer Science
    """
    resume = parse_resume(sample_resume_text, candidate_id="C01")
    assert resume.candidate_id == "C01"
    assert resume.name == "Aarav Sharma"
    assert "React" in resume.skills or "JavaScript" in resume.skills
    assert len(resume.experience) >= 2
    assert len(resume.projects) >= 1
    assert len(resume.education) >= 1


def test_job_description_parsing():
    sample_jd_text = """
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
    - Develop RESTful APIs using Node.js and integrate with client-facing frontend applications.
    - Build responsive web interfaces using React.
    """
    jd = parse_job_description(sample_jd_text)
    assert "Developer" in jd.job_title or "Intern" in jd.job_title
    assert "React" in jd.required_skills or "JavaScript" in jd.required_skills
    assert len(jd.responsibilities) >= 2


def test_pdf_in_memory_creation_and_parsing():
    """Generates an in-memory PDF using PyMuPDF and parses it back."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "John Doe\n\nSkills:\nPython, React, Node.js\n\nExperience:\n- Built REST APIs")
    pdf_bytes = doc.write()
    doc.close()

    text = parse_pdf(pdf_bytes)
    assert "John Doe" in text
    assert "Python" in text
    assert "Built REST APIs" in text
