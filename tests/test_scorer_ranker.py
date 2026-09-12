"""Tests for score calculation and candidate ranking order."""

import json
from pathlib import Path
from backend.models import Resume, JobDescription
from backend.keyword_matcher import match_keywords
from backend.semantic_matcher import compute_semantic_match
from backend.scorer import evaluate_candidate
from backend.ranker import rank_candidates


def test_ranking_hierarchy_strong_medium_weak():
    """Verifies that strong candidates rank strictly higher than medium and weak candidates."""
    data_dir = Path(__file__).parent.parent / "backend" / "data"
    with open(data_dir / "dummy_jd.json", "r", encoding="utf-8") as f:
        jd = JobDescription(**json.load(f))
    with open(data_dir / "dummy_resumes.json", "r", encoding="utf-8") as f:
        resumes = [Resume(**r) for r in json.load(f)]

    evaluations = []
    for r in resumes:
        kw = match_keywords(jd, r)
        sem = compute_semantic_match(jd, r)
        eval_item = evaluate_candidate(r, kw, sem)
        evaluations.append(eval_item)

    ranked = rank_candidates(evaluations)

    eval_by_id = {item.evaluation.candidate_id: item for item in ranked}

    # Verify C01 (Very strong) is ranked higher than C11 (Medium/Frontend) and C18 (Hardware/Weak)
    c01_rank = eval_by_id["C01"].rank
    c11_rank = eval_by_id["C11"].rank
    c18_rank = eval_by_id["C18"].rank

    assert c01_rank < c11_rank, f"C01 rank ({c01_rank}) should be better than C11 ({c11_rank})"
    assert c11_rank < c18_rank, f"C11 rank ({c11_rank}) should be better than C18 ({c18_rank})"
    assert eval_by_id["C01"].evaluation.final_score > eval_by_id["C18"].evaluation.final_score + 40.0


def test_all_candidates_ranked_descending():
    """Verifies all candidates are ranked and score ordering is strictly non-increasing."""
    data_dir = Path(__file__).parent.parent / "backend" / "data"
    with open(data_dir / "dummy_jd.json", "r", encoding="utf-8") as f:
        jd = JobDescription(**json.load(f))
    with open(data_dir / "dummy_resumes.json", "r", encoding="utf-8") as f:
        resumes = [Resume(**r) for r in json.load(f)]

    evaluations = []
    for r in resumes:
        kw = match_keywords(jd, r)
        sem = compute_semantic_match(jd, r)
        eval_item = evaluate_candidate(r, kw, sem)
        evaluations.append(eval_item)

    ranked = rank_candidates(evaluations)

    assert len(ranked) == 18
    for i in range(len(ranked) - 1):
        assert ranked[i].evaluation.final_score >= ranked[i + 1].evaluation.final_score
        assert ranked[i].rank == i + 1
