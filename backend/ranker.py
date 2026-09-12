"""Ranking engine for sorting and ordering all candidates."""

from typing import List, Dict, Optional
from backend.models import CandidateEvaluation, RankedCandidate, Top3Explanation


def rank_candidates(
    evaluations: List[CandidateEvaluation],
    top_3_explanations: Optional[Dict[str, Top3Explanation]] = None
) -> List[RankedCandidate]:
    """Ranks all candidates descending by final score with deterministic tie-breaking."""
    # Deterministic sorting: final_score desc, required_skill_score desc, semantic_score desc
    sorted_evals = sorted(
        evaluations,
        key=lambda e: (e.final_score, e.required_skill_score, e.semantic_score),
        reverse=True
    )

    ranked_list: List[RankedCandidate] = []
    top_3_map = top_3_explanations or {}

    for idx, eval_item in enumerate(sorted_evals, start=1):
        explanation = top_3_map.get(eval_item.candidate_id)
        ranked_list.append(
            RankedCandidate(
                rank=idx,
                evaluation=eval_item,
                explanation=explanation
            )
        )

    return ranked_list
