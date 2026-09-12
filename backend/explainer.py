"""Explanation, comparative analysis, and JD bias inspection engine."""

import re
from typing import Dict, List, Optional
from backend.models import (
    CandidateEvaluation,
    JobDescription,
    Top3Explanation,
    ComparisonResult,
    JDBiasAnalysis,
    JDBiasItem,
)


def generate_top3_explanations(
    top_evaluations: List[CandidateEvaluation],
    jd: JobDescription
) -> List[Top3Explanation]:
    """Generates explainable, evidence-backed justification for top 3 candidates."""
    explanations: List[Top3Explanation] = []

    for rank, cand in enumerate(top_evaluations[:3], start=1):
        # 1. Matched / Missing skills summaries
        matched_str_list = [f"✓ {s}" for s in cand.matched_required_skills]
        missing_str_list = [f"⚠ {s}" for s in cand.missing_required_skills]
        pref_str_list = [f"+ {s}" for s in cand.matched_preferred_skills]

        # 2. Extract key semantic evidence highlights
        semantic_highlights = []
        for ev in cand.key_semantic_matches[:2]:
            semantic_highlights.append(
                f"Demonstrates practical experience in '{ev.candidate_evidence}' (aligned with requirement '{ev.jd_item}', similarity: {int(ev.similarity_score * 100)}%)"
            )

        if not semantic_highlights and cand.experience:
            semantic_highlights.append(f"Relevant background: {cand.experience[0]}")

        # 3. Extract top demonstrated skills with practical context
        strong_skills = []
        for item in cand.skill_analysis:
            if item.matched and (item.experience_alignment in ["Strong", "Moderate"] or item.keyword_evidence >= 0.70):
                strong_skills.append(item.skill)

        top_evidence_skills = strong_skills[:3] if strong_skills else cand.matched_required_skills[:3]
        skills_phrase = ", ".join(top_evidence_skills) if top_evidence_skills else "core competencies"

        # 4. Construct contextual 'why_ranked' narrative
        req_total = cand.required_skills_summary.total or len(jd.required_skills)
        req_matched_count = cand.required_skills_summary.matched_count or len(cand.matched_required_skills)
        match_pct = cand.required_skills_summary.match_percentage or (
            round((req_matched_count / req_total * 100.0), 1) if req_total > 0 else 0.0
        )

        narrative_parts = []
        if req_matched_count == req_total and req_total > 0:
            narrative_parts.append(
                f"Ranked #{rank} because the candidate demonstrates strong practical experience and active proficiency in {skills_phrase}."
            )
        elif req_matched_count >= (req_total * 0.7) and req_total > 0:
            narrative_parts.append(
                f"Ranked #{rank} with strong technical alignment and demonstrated practical depth in {skills_phrase}."
            )
        else:
            narrative_parts.append(
                f"Ranked #{rank} demonstrating solid technical proficiency and semantic project alignment in {skills_phrase}."
            )

        if cand.matched_preferred_skills:
            narrative_parts.append(
                f"Also brings verified expertise in preferred competencies: {', '.join(cand.matched_preferred_skills)}."
            )

        if cand.recency_score >= 60.0:
            narrative_parts.append(
                f"Demonstrates high skill freshness ({cand.recency_score}%) with active production applications in recent roles."
            )

        if cand.semantic_score >= 70:
            narrative_parts.append(
                f"Shows high semantic depth ({cand.semantic_score}/100) across practical full-stack projects."
            )

        if cand.missing_required_skills:
            narrative_parts.append(
                f"Area for onboarding growth: {', '.join(cand.missing_required_skills)}."
            )

        why_ranked = " ".join(narrative_parts)

        explanations.append(
            Top3Explanation(
                rank=rank,
                candidate_id=cand.candidate_id,
                name=cand.name,
                score=cand.final_score,
                keyword_score=cand.keyword_score,
                semantic_score=cand.semantic_score,
                recency_score=cand.recency_score,
                why_ranked=why_ranked,
                matched_count=req_matched_count,
                total_required=req_total,
                match_percentage=match_pct,
                required_skills_summary=cand.required_skills_summary,
                skill_analysis=cand.skill_analysis,
                matched_skills=matched_str_list,
                missing_skills=missing_str_list,
                matched_preferred=pref_str_list,
                semantic_evidence=semantic_highlights,
                skill_recency_evidence=cand.skill_recency_evidence,
            )
        )

    return explanations



def compare_candidates(
    cand_a: CandidateEvaluation,
    cand_b: CandidateEvaluation,
    jd: JobDescription
) -> ComparisonResult:
    """Generates structured 'Why Candidate A over Candidate B' comparative analysis."""
    req_total = len(jd.required_skills)

    # Determine higher ranked candidate
    if cand_a.final_score >= cand_b.final_score:
        winner_id = cand_a.candidate_id
        winner_name = cand_a.name
        higher = cand_a
        lower = cand_b
    else:
        winner_id = cand_b.candidate_id
        winner_name = cand_b.name
        higher = cand_b
        lower = cand_a

    score_delta = round(abs(cand_a.final_score - cand_b.final_score), 1)

    # Key differentiators based on semantic alignment, freshness, depth, and evidence
    differentiators: List[str] = []

    sem_diff = higher.semantic_score - lower.semantic_score
    if sem_diff >= 5.0:
        differentiators.append(
            f"{higher.name} exhibits stronger contextual project alignment ({higher.semantic_score}% vs {lower.semantic_score}%, +{round(sem_diff, 1)}% semantic advantage)."
        )
    elif sem_diff <= -5.0:
        differentiators.append(
            f"{lower.name} has higher contextual semantic score ({lower.semantic_score}% vs {higher.semantic_score}%), but lacks key technical depth."
        )

    # Recency & Freshness differentiator
    rec_diff = higher.recency_score - lower.recency_score
    if rec_diff >= 8.0:
        differentiators.append(
            f"{higher.name} demonstrates superior skill recency and active professional application ({higher.recency_score}% vs {lower.recency_score}% freshness index)."
        )

    # Evidence Depth & Practical Quality differentiator
    depth_higher = getattr(higher, "evidence_depth_score", 0.0)
    depth_lower = getattr(lower, "evidence_depth_score", 0.0)
    depth_diff = depth_higher - depth_lower
    if depth_diff >= 6.0:
        differentiators.append(
            f"{higher.name} demonstrates superior practical evidence depth ({depth_higher}% vs {depth_lower}%), backing skills with concrete project and work implementations rather than static listings."
        )

    pref_diff = len(higher.matched_preferred_skills) - len(lower.matched_preferred_skills)
    if pref_diff > 0:
        differentiators.append(
            f"{higher.name} brings bonus preferred skills: {', '.join(higher.matched_preferred_skills)}."
        )

    # Unique skills present in higher candidate but missing in lower
    unique_to_higher = set(higher.matched_required_skills) - set(lower.matched_required_skills)
    if unique_to_higher:
        differentiators.append(
            f"Key missing skills in {lower.name} present in {higher.name}: {', '.join(unique_to_higher)}."
        )

    # Summary statement
    if higher.keyword_score > lower.keyword_score and higher.semantic_score >= lower.semantic_score:
        summary = f"{higher.name} ranks higher primarily because they satisfy more explicit required skills while maintaining superior semantic project alignment."
    elif higher.keyword_score > lower.keyword_score:
        summary = f"{higher.name} ranks higher due to stronger compliance with core mandatory technical requirements."
    elif higher.semantic_score > lower.semantic_score:
        summary = f"{higher.name} ranks higher because their practical project and work experience demonstrates significantly deeper relevant engineering experience."
    else:
        summary = f"{higher.name} edges out {lower.name} with a balanced combination of skill coverage and hands-on relevance."

    return ComparisonResult(
        candidate_a_id=cand_a.candidate_id,
        candidate_a_name=cand_a.name,
        candidate_a_score=cand_a.final_score,
        candidate_a_keyword=cand_a.keyword_score,
        candidate_a_semantic=cand_a.semantic_score,
        candidate_a_req_matched=len(cand_a.matched_required_skills),
        candidate_a_req_total=req_total,
        candidate_a_missing=cand_a.missing_required_skills,
        candidate_b_id=cand_b.candidate_id,
        candidate_b_name=cand_b.name,
        candidate_b_score=cand_b.final_score,
        candidate_b_keyword=cand_b.keyword_score,
        candidate_b_semantic=cand_b.semantic_score,
        candidate_b_req_matched=len(cand_b.matched_required_skills),
        candidate_b_req_total=req_total,
        candidate_b_missing=cand_b.missing_required_skills,
        higher_ranked_candidate=winner_name,
        score_delta=score_delta,
        summary=summary,
        key_differentiators=differentiators,
    )


def analyze_jd_bias(jd: JobDescription) -> JDBiasAnalysis:
    """Inspects Job Description for potential bias, unrealistic constraints, or exclusionary phrasing."""
    flags: List[JDBiasItem] = []
    full_text = f"{jd.description} {' '.join(jd.responsibilities)} {' '.join(jd.required_skills)} {' '.join(jd.education_requirements)} {jd.raw_text}"
    full_text_lower = full_text.lower()

    # 1. Elite Institution / Tier-1 bias
    if re.search(r"\b(tier[- ]?1|ivy league|top tier|premier institute|iit|nit|only from)\b", full_text_lower):
        flags.append(
            JDBiasItem(
                category="Institution Elitism",
                flagged_text="Mentions restrictive institution requirements (e.g., Tier-1 / Premier institute)",
                explanation="Restricting to specific elite universities excludes talented self-taught or diverse candidates who meet all technical competencies.",
                recommendation="Focus criteria strictly on demonstrable software engineering skills and project portfolio."
            )
        )

    # 2. Aggressive / Gender-coded jargon
    masculine_jargon = re.findall(r"\b(rockstar|ninja|guru|wizard|crush it|work hard play hard|aggressive|dominant)\b", full_text_lower)
    if masculine_jargon:
        flags.append(
            JDBiasItem(
                category="Hyper-competitive / Gendered Wording",
                flagged_text=", ".join(set(masculine_jargon)),
                explanation="Terms like 'ninja', 'rockstar', or hyper-aggressive phrasing have been shown to deter qualified women and collaborative candidates.",
                recommendation="Replace with collaborative terms such as 'collaborative engineer', 'motivated developer', or 'problem solver'."
            )
        )

    # 3. Excessive experience requirements for intern/junior roles
    if "intern" in jd.job_title.lower() or "junior" in jd.job_title.lower():
        exp_matches = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", full_text_lower)
        for exp in exp_matches:
            if int(exp) >= 3:
                flags.append(
                    JDBiasItem(
                        category="Unrealistic Experience Gate",
                        flagged_text=f"{exp}+ years experience required for an intern/junior opening",
                        explanation=f"Demanding {exp}+ years of industry experience for an internship or entry-level role is contradictory and filters out promising students.",
                        recommendation="Change requirement to 'Hands-on coursework, personal projects, or prior internship experience'."
                    )
                )
                break

    # 4. Strict Degree Requirements
    if re.search(r"\b(b\.?tech only|cs degree mandatory|computer science degree required)\b", full_text_lower):
        flags.append(
            JDBiasItem(
                category="Degree Credentialism",
                flagged_text="Strict mandatory Computer Science degree constraint",
                explanation="Excludes capable candidates from Information Technology, Data Science, or Bootcamp backgrounds with equivalent coding proficiency.",
                recommendation="Use 'Bachelor's degree in CS/IT, related quantitative field, or equivalent practical project experience'."
            )
        )

    has_flags = len(flags) > 0
    summary = (
        f"Identified {len(flags)} potential bias or overly narrow constraint(s) in the Job Description."
        if has_flags
        else "Job Description phrasing is inclusive, competency-focused, and well-balanced."
    )

    return JDBiasAnalysis(
        has_flags=has_flags,
        summary=summary,
        flags=flags
    )
