"""Text cleaning and normalization utilities for InternLoom."""

import re
from typing import List


def clean_text(text: str) -> str:
    """Cleans and standardizes raw text from PDFs or inputs.
    
    Handles:
    - Normalizing unicode bullets and strange bullet points.
    - Stripping page numbers and PDF header/footer artifacts.
    - Collapsing excessive blank lines while preserving logical paragraphs.
    - Preserving technical terms (Node.js, C++, .NET, React.js, CI/CD, etc.).
    """
    if not text:
        return ""

    # Replace windows line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize various bullet points to standard dash
    bullet_regex = r"[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25AB\u25CF\u25CB\u25C6\u27A2\u279C\u2705\u2714\u2713\u25B6\u25BA\uF0A7\uF0B7\uF076]"
    text = re.sub(bullet_regex, "\n- ", text)

    # Remove typical page numbering artifacts like "Page 1 of 3", "Page 2/4", "- Page 1 -"
    text = re.sub(r"(?i)\bpage\s+\d+\s*(?:of|/)\s*\d+\b", "", text)
    text = re.sub(r"(?i)\bpage\s+\d+\b", "", text)
    text = re.sub(r"-+\s*\d+\s*-+", "", text)

    # Clean non-printable control characters except tabs and newlines
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Normalize horizontal spaces/tabs to a single space
    lines = []
    for line in text.split("\n"):
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line_clean)

    # Rejoin and normalize multiple consecutive empty lines to maximum of 2
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def extract_bullet_points(section_text: str) -> List[str]:
    """Extracts clean bullet items or individual lines from a section."""
    if not section_text:
        return []

    lines = section_text.split("\n")
    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Strip leading bullet indicators, numbers, symbols, and non-ascii artifacts
        cleaned_line = re.sub(r"^[^a-zA-Z0-9(\[\"\'\s]+", "", line).strip()
        cleaned_line = re.sub(r"^\d+[\.\)\-]\s*", "", cleaned_line).strip()
        if cleaned_line and len(cleaned_line) > 2:
            items.append(cleaned_line)

    return items

