"""Tests for top-3 explanation generation, candidate comparison, and JD bias analysis."""

from backend.models import Resume, JobDescription, CandidateEvaluation, SemanticEvidenceItem
from backend.explainer import generate_top3_explanations, compare_candidates, analyze_jd_bias


def test_top3_explanations_structure():
    jd = JobDescription(
        job_title="Junior Full Stack Developer",
        required_skills=["JavaScript", "React", "Node.js"],
        preferred_skills=["Docker"]
    )

    evals = [
        CandidateEvaluation(
            candidate_id="C01",
            name="Alice",
            final_score=92.0,
            keyword_score=90.0,
            semantic_score=94.0,
            required_skill_score=100.0,
            preferred_skill_score=100.0,
            matched_required_skills=["JavaScript", "React", "Node.js"],
            missing_required_skills=[],
            matched_preferred_skills=["Docker"],
            missing_preferred_skills=[],
            key_semantic_matches=[
                SemanticEvidenceItem(
                    jd_item="Develop APIs with Node.js",
                    candidate_evidence="Built scalable REST APIs in Express",
                    similarity_score=0.88
                )
            ]
        ),
        CandidateEvaluation(
            candidate_id="C02",
            name="Bob",
            final_score=85.0,
            keyword_score=80.0,
            semantic_score=90.0,
            required_skill_score=66.7,
            preferred_skill_score=100.0,
            matched_required_skills=["JavaScript", "React"],
            missing_required_skills=["Node.js"],
            matched_preferred_skills=["Docker"],
            missing_preferred_skills=[],
            key_semantic_matches=[]
        ),
        CandidateEvaluation(
            candidate_id="C03",
            name="Charlie",
            final_score=78.0,
            keyword_score=75.0,
            semantic_score=81.0,
            required_skill_score=66.7,
            preferred_skill_score=0.0,
            matched_required_skills=["React", "Node.js"],
            missing_required_skills=["JavaScript"],
            matched_preferred_skills=[],
            missing_preferred_skills=["Docker"],
            key_semantic_matches=[]
        )
    ]

    explanations = generate_top3_explanations(evals, jd)
    assert len(explanations) == 3
    assert explanations[0].rank == 1
    assert explanations[0].candidate_id == "C01"
    assert "✓ React" in explanations[0].matched_skills
    assert len(explanations[0].missing_skills) == 0
    assert len(explanations[1].missing_skills) == 1
    assert "Node.js" in explanations[1].missing_skills[0]


def test_compare_candidates_structured_differentiators():
    jd = JobDescription(
        job_title="Full Stack Developer",
        required_skills=["React", "Node.js", "MongoDB"],
        preferred_skills=["AWS"]
    )

    cand_a = CandidateEvaluation(
        candidate_id="C01",
        name="Candidate A",
        final_score=91.5,
        keyword_score=89.0,
        semantic_score=94.0,
        required_skill_score=100.0,
        preferred_skill_score=100.0,
        matched_required_skills=["React", "Node.js", "MongoDB"],
        missing_required_skills=[],
        matched_preferred_skills=["AWS"],
        missing_preferred_skills=[],
        key_semantic_matches=[]
    )

    cand_b = CandidateEvaluation(
        candidate_id="C02",
        name="Candidate B",
        final_score=84.2,
        keyword_score=78.0,
        semantic_score=90.0,
        required_skill_score=66.7,
        preferred_skill_score=0.0,
        matched_required_skills=["React", "Node.js"],
        missing_required_skills=["MongoDB"],
        matched_preferred_skills=[],
        missing_preferred_skills=["AWS"],
        key_semantic_matches=[]
    )

    comp = compare_candidates(cand_a, cand_b, jd)
    assert comp.higher_ranked_candidate == "Candidate A"
    assert comp.candidate_a_req_matched == 3
    assert comp.candidate_b_req_matched == 2
    assert "MongoDB" in comp.candidate_b_missing
    assert len(comp.key_differentiators) > 0


def test_analyze_jd_bias_flags_exclusionary_terms():
    jd = JobDescription(
        job_title="Junior Developer Intern",
        required_skills=["JavaScript", "React"],
        raw_text="We need a rockstar 10x ninja only from Tier-1 premier institutes with 5+ years experience."
    )

    analysis = analyze_jd_bias(jd)
    assert analysis.has_flags is True
    assert len(analysis.flags) >= 2
    categories = [f.category for f in analysis.flags]
    assert "Institution Elitism" in categories
    assert "Hyper-competitive / Gendered Wording" in categories
