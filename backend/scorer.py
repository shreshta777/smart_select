"""Scoring engine combining evidence-weighted keywords, semantic alignment, evidence depth, and skill recency."""

import re
from typing import List, Optional, Dict
from backend.models import (
    CandidateEvaluation,
    KeywordMatchResult,
    SemanticMatchResult,
    SkillRecencyEvidence,
    SkillAnalysisItem,
    RequiredSkillsSummary,
    SkillMatchDetail,
    Resume,
)


def build_skill_analysis(
    kw_result: KeywordMatchResult,
    sem_result: SemanticMatchResult,
    skill_recency_evidence: Optional[List[SkillRecencyEvidence]] = None,
) -> List[SkillAnalysisItem]:
    """Builds transparent, deterministic per-skill analysis items from real multi-vector backend signals."""
    analysis_items: List[SkillAnalysisItem] = []
    rec_map: Dict[str, SkillRecencyEvidence] = {}
    if skill_recency_evidence:
        for r in skill_recency_evidence:
            rec_map[r.skill.lower().strip()] = r

    # Map semantic evidence to skills
    sem_matches = sem_result.key_semantic_matches or []

    for detail in kw_result.skill_match_details:
        skill_norm = detail.skill.lower().strip()
        rec_item = rec_map.get(skill_norm)

        # 1. Match status & keyword evidence
        matched = detail.strength >= 0.35
        kw_ev = round(detail.strength, 2)
        if kw_ev >= 0.85:
            kw_label = "Strong"
        elif kw_ev >= 0.65:
            kw_label = "Moderate"
        elif kw_ev >= 0.35:
            kw_label = "Weak"
        else:
            kw_label = "Missing"

        # 2. Recency & Context signals
        if rec_item and rec_item.found:
            last_used = rec_item.last_used
            usage_context = rec_item.experience_context
            freshness_score = round(rec_item.freshness_score, 1)
            proj_count = max(detail.project_count, rec_item.project_count)
            in_curr_role = rec_item.used_in_current_role or detail.in_current_role
        else:
            last_used = None
            usage_context = "missing" if not matched else ("skills_section" if detail.found_in_skills_list else "unknown")
            freshness_score = 0.0 if not matched else 30.0
            proj_count = detail.project_count
            in_curr_role = detail.in_current_role

        # 3. Semantic relevance
        best_sem_sim = 0.0
        for sm in sem_matches:
            if skill_norm in sm.jd_item.lower() or skill_norm in sm.candidate_evidence.lower():
                if sm.similarity_score > best_sem_sim:
                    best_sem_sim = sm.similarity_score

        if best_sem_sim > 0:
            sem_rel = round(best_sem_sim, 2)
        elif matched:
            sem_rel = round(min(0.95, 0.40 + (kw_ev * 0.45)), 2)
        else:
            sem_rel = 0.0

        if sem_rel >= 0.70:
            sem_label = "High"
        elif sem_rel >= 0.40:
            sem_label = "Medium"
        else:
            sem_label = "Low"

        # 4. Experience alignment category
        if not matched:
            exp_alignment = "None"
        elif in_curr_role or (detail.evidence_tier == "deep_experience" and len(detail.action_verbs) >= 1) or (freshness_score >= 70 and usage_context in ["current_role", "work_experience"]):
            exp_alignment = "Strong"
        elif detail.evidence_tier == "project_evidence" or usage_context in ["internship", "project"] or proj_count >= 1 or freshness_score >= 50:
            exp_alignment = "Moderate"
        else:
            exp_alignment = "Weak"

        # 5. Deterministic per-skill score (0-100)
        if not matched:
            skill_score = 0.0
        else:
            align_bonus = 100.0 if exp_alignment == "Strong" else (70.0 if exp_alignment == "Moderate" else 40.0)
            raw_skill_score = (
                (0.40 * (kw_ev * 100.0)) +
                (0.25 * (sem_rel * 100.0)) +
                (0.20 * freshness_score) +
                (0.15 * align_bonus)
            )
            skill_score = round(min(100.0, max(0.0, raw_skill_score)), 1)

        analysis_items.append(
            SkillAnalysisItem(
                skill=detail.skill,
                matched=matched,
                is_required=detail.is_required,
                skill_score=skill_score,
                keyword_evidence=kw_ev,
                keyword_evidence_label=kw_label,
                semantic_relevance=sem_rel,
                semantic_relevance_label=sem_label,
                freshness_score=freshness_score,
                experience_alignment=exp_alignment,
                last_used=last_used,
                usage_context=usage_context,
                project_count=proj_count,
                action_verbs=detail.action_verbs,
                evidence_snippets=detail.evidence_snippets,
                explanation=detail.explanation
            )
        )

    return analysis_items


def evaluate_candidate(
    resume: Resume,
    kw_result: KeywordMatchResult,
    sem_result: SemanticMatchResult,
    recency_score: float = 0.0,
    skill_recency_evidence: Optional[List[SkillRecencyEvidence]] = None,
    keyword_weight: float = 0.5,
    semantic_weight: float = 0.5,
    recency_weight: float = 0.15,
) -> CandidateEvaluation:
    """Combines keyword evidence, semantic depth, recency, and experience quality into an explainable score."""
    # 1. Normalize user-configurable keyword & semantic weights
    total_w = keyword_weight + semantic_weight
    w_kw = keyword_weight / total_w if total_w > 0 else 0.5
    w_sem = semantic_weight / total_w if total_w > 0 else 0.5

    # 2. Base match combining evidence-weighted keyword score and semantic score
    base_match = (w_kw * kw_result.keyword_score) + (w_sem * sem_result.semantic_score)

    # 3. Quality & Evidence Depth signal (combining practical project depth & skill recency)
    evidence_depth = getattr(kw_result, "evidence_depth_score", 0.0)
    if recency_score > 0 and evidence_depth > 0:
        quality_score = (0.50 * recency_score) + (0.50 * evidence_depth)
    elif recency_score > 0:
        quality_score = recency_score
    elif evidence_depth > 0:
        quality_score = evidence_depth
    else:
        quality_score = base_match

    # 4. Core composite score (75% base match + 25% practical quality & depth)
    composite_score = (0.75 * base_match) + (0.25 * quality_score)

    # 5. Missing required skill penalty (penalize proportionally if core skills are missing)
    total_req = len(kw_result.matched_required_skills) + len(kw_result.missing_required_skills)
    missing_req_count = len(kw_result.missing_required_skills)
    matched_req_count = len(kw_result.matched_required_skills)
    missing_penalty = 0.0
    if total_req > 0 and missing_req_count > 0:
        missing_penalty = (missing_req_count / total_req) * 12.0

    # 6. Preferred skills bonus (up to +4.0 points for proven bonus skills)
    total_pref = len(kw_result.matched_preferred_skills) + len(kw_result.missing_preferred_skills)
    matched_pref_count = len(kw_result.matched_preferred_skills)
    pref_bonus = 0.0
    if total_pref > 0 and matched_pref_count > 0:
        pref_bonus = (matched_pref_count / total_pref) * 4.0

    # 7. Final bounded score
    final_score = composite_score + pref_bonus - missing_penalty
    final_score = round(min(100.0, max(0.0, final_score)), 1)

    # 8. Build structured RequiredSkillsSummary
    match_pct = round((matched_req_count / total_req * 100.0), 1) if total_req > 0 else 0.0
    req_summary = RequiredSkillsSummary(
        total=total_req,
        matched_count=matched_req_count,
        missing_count=missing_req_count,
        match_percentage=match_pct,
        matched=kw_result.matched_required_skills,
        missing=kw_result.missing_required_skills,
    )

    # 9. Build per-skill analysis items
    skill_analysis = build_skill_analysis(
        kw_result=kw_result,
        sem_result=sem_result,
        skill_recency_evidence=skill_recency_evidence,
    )

    return CandidateEvaluation(
        candidate_id=resume.candidate_id,
        name=resume.name,
        final_score=final_score,
        keyword_score=kw_result.keyword_score,
        semantic_score=sem_result.semantic_score,
        recency_score=round(recency_score, 1),
        evidence_depth_score=round(evidence_depth, 1),
        required_skill_score=kw_result.required_skill_score,
        preferred_skill_score=kw_result.preferred_skill_score,
        matched_required_skills=kw_result.matched_required_skills,
        missing_required_skills=kw_result.missing_required_skills,
        matched_preferred_skills=kw_result.matched_preferred_skills,
        missing_preferred_skills=kw_result.missing_preferred_skills,
        required_skills_summary=req_summary,
        skill_analysis=skill_analysis,
        skill_match_details=kw_result.skill_match_details,
        key_semantic_matches=sem_result.key_semantic_matches,
        skill_recency_evidence=skill_recency_evidence or [],
        skills=resume.skills,
        experience=resume.experience,
        projects=resume.projects,
        education=resume.education,
    )



