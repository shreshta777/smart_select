"""Skill Recency & Relevance Engine.

Evaluates skill usage recency, professional context, project frequency,
and freshness decay across resume sections without LLM hallucination.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from rapidfuzz import fuzz

from backend.models import (
    JobDescription,
    Resume,
    SkillRecencyEvidence,
)
from backend.keyword_matcher import (
    CANONICAL_SKILL_MAP,
    normalize_token,
    get_canonical_name,
)

# Context base scores (0-100)
CONTEXT_BASE_SCORES: Dict[str, float] = {
    "current_role": 95.0,
    "work_experience": 85.0,
    "internship": 80.0,
    "project": 72.0,
    "certification": 70.0,
    "college_project": 55.0,
    "education": 50.0,
    "skills_section": 50.0,
    "unknown": 50.0,
}

# Context priority rank (higher index = higher precedence)
CONTEXT_PRIORITY: Dict[str, int] = {
    "missing": 0,
    "unknown": 1,
    "skills_section": 2,
    "education": 3,
    "college_project": 4,
    "certification": 5,
    "project": 6,
    "internship": 7,
    "work_experience": 8,
    "current_role": 9,
}

YEAR_REGEX = re.compile(r"\b(19\d\d|20\d\d)\b")
RANGE_PRESENT_REGEX = re.compile(
    r"(?i)\b(19\d\d|20\d\d)\s*(?:-|–|—|to)\s*(present|current|now|ongoing|date)\b"
)
RANGE_YEARS_REGEX = re.compile(
    r"\b(19\d\d|20\d\d)\s*(?:-|–|—|to)\s*(19\d\d|20\d\d)\b"
)
CURRENT_ROLE_KEYWORDS = re.compile(
    r"(?i)\b(present|current role|currently working|now|ongoing)\b"
)
COLLEGE_PROJECT_KEYWORDS = re.compile(
    r"(?i)\b(college|university|academic|coursework|course project|final year|capstone|b\.?tech|b\.?e\.?|m\.?tech|semester)\b"
)
INTERN_KEYWORDS = re.compile(r"(?i)\b(intern|internship|trainee|apprentice)\b")


def extract_years_from_text(text: str) -> List[int]:
    """Extracts valid 4-digit calendar years from a text segment."""
    if not text:
        return []
    matches = YEAR_REGEX.findall(text)
    years: List[int] = []
    for m in matches:
        try:
            y = int(m)
            if 1990 <= y <= 2035:
                years.append(y)
        except ValueError:
            continue
    return years


def determine_reference_year(resume: Resume, fallback_year: int = 2026) -> int:
    """Determines the baseline reference year for recency decay calculation."""
    all_text = " ".join([
        resume.raw_text,
        " ".join(resume.experience),
        " ".join(resume.projects),
        " ".join(resume.education),
    ])
    years = extract_years_from_text(all_text)
    if years:
        max_y = max(years)
        return max(2024, min(fallback_year, max_y))
    return fallback_year


def skill_matches_text_segment(skill: str, text: str) -> bool:
    """Checks if a skill or any of its canonical aliases is mentioned in a text segment."""
    if not text or not skill:
        return False

    norm_skill = normalize_token(skill)
    canon_skill = get_canonical_name(skill)
    text_lower = text.lower()

    aliases_to_check = [norm_skill]
    if canon_skill in CANONICAL_SKILL_MAP:
        aliases_to_check.extend(CANONICAL_SKILL_MAP[canon_skill])

    for alias in aliases_to_check:
        escaped_alias = re.escape(alias)
        if alias in ["c", "r"]:
            pattern = rf"(?:\b|(?<=[^a-zA-Z0-9])){escaped_alias}(?:\b|(?=[^a-zA-Z0-9]))"
        elif " " in alias or "." in alias or "+" in alias or "#" in alias or "/" in alias:
            pattern = rf"(?:\b|(?<=[^a-zA-Z0-9])){escaped_alias}(?:\b|(?=[^a-zA-Z0-9]))"
        else:
            pattern = rf"\b{escaped_alias}\b"

        if re.search(pattern, text_lower):
            return True

    # Fallback to high ratio fuzzy token matching for long phrases
    if len(norm_skill) > 5 and fuzz.partial_ratio(norm_skill, text_lower) >= 92:
        return True

    return False


def compute_skill_freshness(
    found: bool,
    last_used: Optional[int],
    used_in_current_role: bool,
    project_count: int,
    experience_context: str,
    ref_year: int = 2026,
) -> float:
    """Calculates a deterministic freshness score (0-100) using transparent rule-based decay."""
    if not found or experience_context == "missing":
        return 0.0

    base = CONTEXT_BASE_SCORES.get(experience_context, 50.0)

    # Age Decay factor
    if used_in_current_role:
        decay = 1.00
    elif last_used is not None:
        delta = max(0, ref_year - last_used)
        if delta == 0:
            decay = 1.00
        elif delta == 1:
            decay = 0.95
        elif delta == 2:
            decay = 0.88
        elif delta == 3:
            decay = 0.78
        elif delta == 4:
            decay = 0.68
        elif delta == 5:
            decay = 0.55
        else:
            decay = max(0.20, 0.55 - 0.06 * (delta - 5))
    else:
        # Conservative fallback when dates are missing without hallucinating
        decay = 0.75

    # Project / Usage Depth bonus (up to 15 bonus points for multi-project proven track record)
    depth_bonus = min(15.0, max(0, project_count - 1) * 3.0)

    raw_score = (base * decay) + depth_bonus

    # Strong boost guarantee for verified current role usage
    if used_in_current_role:
        raw_score = max(raw_score, 92.0)

    return round(min(100.0, max(10.0, raw_score)), 1)


def evaluate_skill_recency(
    target_skill: str,
    resume: Resume,
    ref_year: int = 2026,
) -> SkillRecencyEvidence:
    """Extracts deterministic recency and relevance evidence for a single skill."""
    years_found: List[int] = []
    used_in_current_role = False
    project_count = 0
    best_context = "unknown"
    skill_found_anywhere = False

    # 1. Inspect Experience Section
    for exp_entry in resume.experience:
        if skill_matches_text_segment(target_skill, exp_entry):
            skill_found_anywhere = True
            project_count += 1

            has_present_range = bool(RANGE_PRESENT_REGEX.search(exp_entry))
            has_current_keyword = bool(CURRENT_ROLE_KEYWORDS.search(exp_entry))

            if has_present_range or has_current_keyword:
                used_in_current_role = True
                years_found.append(ref_year)
                context = "current_role"
            elif INTERN_KEYWORDS.search(exp_entry):
                context = "internship"
            else:
                context = "work_experience"

            entry_years = extract_years_from_text(exp_entry)
            years_found.extend(entry_years)

            if CONTEXT_PRIORITY.get(context, 0) > CONTEXT_PRIORITY.get(best_context, 0):
                best_context = context

    # 2. Inspect Projects Section
    for proj_entry in resume.projects:
        if skill_matches_text_segment(target_skill, proj_entry):
            skill_found_anywhere = True
            project_count += 1

            proj_years = extract_years_from_text(proj_entry)
            years_found.extend(proj_years)

            if COLLEGE_PROJECT_KEYWORDS.search(proj_entry):
                context = "college_project"
            else:
                context = "project"

            if CONTEXT_PRIORITY.get(context, 0) > CONTEXT_PRIORITY.get(best_context, 0):
                best_context = context

    # 3. Inspect Certifications Section
    for cert_entry in resume.certifications:
        if skill_matches_text_segment(target_skill, cert_entry):
            skill_found_anywhere = True
            cert_years = extract_years_from_text(cert_entry)
            years_found.extend(cert_years)
            context = "certification"

            if CONTEXT_PRIORITY.get(context, 0) > CONTEXT_PRIORITY.get(best_context, 0):
                best_context = context

    # 4. Inspect Education Section
    for edu_entry in resume.education:
        if skill_matches_text_segment(target_skill, edu_entry):
            skill_found_anywhere = True
            edu_years = extract_years_from_text(edu_entry)
            years_found.extend(edu_years)
            context = "education"

            if CONTEXT_PRIORITY.get(context, 0) > CONTEXT_PRIORITY.get(best_context, 0):
                best_context = context

    # 5. Check Explicit Skills list (if not found in experience/projects)
    if not skill_found_anywhere:
        for sk in resume.skills:
            if normalize_token(sk) == normalize_token(target_skill) or get_canonical_name(sk) == get_canonical_name(target_skill):
                skill_found_anywhere = True
                best_context = "skills_section"
                break

    # 6. Fallback scan on raw_text if still not detected
    if not skill_found_anywhere and skill_matches_text_segment(target_skill, resume.raw_text):
        skill_found_anywhere = True
        best_context = "unknown"
        raw_years = extract_years_from_text(resume.raw_text)
        years_found.extend(raw_years)

    if not skill_found_anywhere:
        return SkillRecencyEvidence(
            skill=target_skill,
            found=False,
            last_used=None,
            used_in_current_role=False,
            project_count=0,
            experience_context="missing",
            freshness_score=0.0,
        )

    last_used = max(years_found) if years_found else None

    if used_in_current_role:
        last_used = max(last_used, ref_year) if last_used is not None else ref_year

    freshness = compute_skill_freshness(
        found=True,
        last_used=last_used,
        used_in_current_role=used_in_current_role,
        project_count=project_count,
        experience_context=best_context,
        ref_year=ref_year,
    )

    return SkillRecencyEvidence(
        skill=target_skill,
        found=True,
        last_used=last_used,
        used_in_current_role=used_in_current_role,
        project_count=project_count,
        experience_context=best_context,
        freshness_score=freshness,
    )


def extract_candidate_skill_recency(
    jd: JobDescription,
    resume: Resume,
) -> Tuple[List[SkillRecencyEvidence], float]:
    """Evaluates all required and preferred skills against the candidate resume for recency."""
    ref_year = determine_reference_year(resume)
    all_target_skills = list(dict.fromkeys(jd.required_skills + jd.preferred_skills))

    evidence_list: List[SkillRecencyEvidence] = []
    matched_freshness_scores: List[float] = []

    for skill in all_target_skills:
        ev = evaluate_skill_recency(skill, resume, ref_year=ref_year)
        evidence_list.append(ev)
        if ev.found:
            matched_freshness_scores.append(ev.freshness_score)

    if matched_freshness_scores:
        aggregate_recency = round(
            sum(matched_freshness_scores) / len(matched_freshness_scores), 1
        )
    else:
        aggregate_recency = 0.0

    return evidence_list, aggregate_recency
