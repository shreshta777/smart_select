"""Unit and integration tests for Skill Recency & Relevance Engine."""

import pytest
from backend.models import JobDescription, Resume, KeywordMatchResult, SemanticMatchResult
from backend.recency import (
    evaluate_skill_recency,
    extract_candidate_skill_recency,
    compute_skill_freshness,
    extract_years_from_text,
)
from backend.scorer import evaluate_candidate
from backend.main import run_pipeline


def test_extract_years_from_text():
    text1 = "Senior Developer (2022 - 2025): Built scalable services."
    assert extract_years_from_text(text1) == [2022, 2025]

    text2 = "No years mentioned here."
    assert extract_years_from_text(text2) == []

    text3 = "Started in 2019, graduated in 2023."
    assert extract_years_from_text(text3) == [2019, 2023]


def test_candidate_a_current_role_high_freshness():
    """Candidate A: Java in current role (2025 / Present) -> High Freshness."""
    resume_a = Resume(
        candidate_id="C_A",
        name="Candidate A (Current Role)",
        skills=["Java", "Spring Boot", "Docker"],
        experience=[
            "Lead Backend Engineer at TechCorp (2024 - Present): Architected microservices with Java and Spring Boot across 4 production clusters.",
            "Software Developer (2022 - 2024): Built REST APIs using Java and Docker."
        ],
        projects=[
            "Enterprise Payment Gateway (2025): Built Java transactions pipeline.",
            "High Throughput Messaging (2024): Java event stream."
        ],
        education=["B.Tech Computer Science (2018 - 2022)"]
    )

    ev = evaluate_skill_recency("Java", resume_a, ref_year=2026)
    assert ev.found is True
    assert ev.used_in_current_role is True
    assert ev.last_used == 2026 or ev.last_used == 2025
    assert ev.experience_context == "current_role"
    assert ev.project_count >= 3
    assert ev.freshness_score >= 90.0


def test_candidate_b_old_college_project_low_freshness():
    """Candidate B: Java only in old college project (2020) -> Low Freshness."""
    resume_b = Resume(
        candidate_id="C_B",
        name="Candidate B (Old College Project)",
        skills=["Python", "Java", "SQL"],
        experience=[
            "Data Analyst at AnalyticsHub (2024 - Present): Working on Python, Pandas, and SQL dashboards."
        ],
        projects=[
            "College Final Year Project (2020): Simple library management software written in Java."
        ],
        education=["B.Tech in Computer Science, College of Engineering (2016 - 2020)"]
    )

    ev = evaluate_skill_recency("Java", resume_b, ref_year=2026)
    assert ev.found is True
    assert ev.used_in_current_role is False
    assert ev.last_used == 2020
    assert ev.experience_context == "college_project"
    assert ev.project_count == 1
    # 2020 vs 2026 (6 years delta) + college_project base (55) -> decay down to < 45
    assert ev.freshness_score <= 45.0


def test_candidate_c_no_dates_conservative_fallback():
    """Candidate C: Java listed only in skills section without dates -> Safe fallback."""
    resume_c = Resume(
        candidate_id="C_C",
        name="Candidate C (No Dates)",
        skills=["Java", "Docker"],
        experience=["Software development across various applications."],
        projects=["Web system development."],
        education=["Computer Science degree."]
    )

    ev = evaluate_skill_recency("Java", resume_c, ref_year=2026)
    assert ev.found is True
    assert ev.used_in_current_role is False
    assert ev.last_used is None
    assert ev.experience_context == "skills_section"
    # Should not crash and use conservative fallback (around 35 - 50)
    assert 30.0 <= ev.freshness_score <= 50.0


def test_recency_impact_on_scoring_and_ranking():
    """Verifies that Candidate A (current role Java) ranks above Candidate B (old college Java)
    when keyword and semantic scores are comparable."""
    jd = JobDescription(
        job_title="Senior Java Engineer",
        required_skills=["Java", "Docker"],
        preferred_skills=[]
    )

    resume_a = Resume(
        candidate_id="C_A",
        name="Candidate A (Current Role)",
        skills=["Java", "Docker"],
        experience=["Senior Backend Developer (2024 - Present): Building Java and Docker microservices."],
        projects=["Cloud Payment Processing (2025): High scale Java platform."]
    )

    resume_b = Resume(
        candidate_id="C_B",
        name="Candidate B (Old Project)",
        skills=["Java", "Docker"],
        experience=["Technical Writer (2024 - Present): Writing software documentation for Docker."],
        projects=["College Project (2019): Academic Java console program."]
    )

    response = run_pipeline(jd, [resume_b, resume_a], keyword_weight=0.5, semantic_weight=0.5)

    # Candidate A should be Rank 1 due to higher skill recency and active current role freshness
    assert response.rankings[0].evaluation.candidate_id == "C_A"
    assert response.rankings[0].evaluation.recency_score > response.rankings[1].evaluation.recency_score
    assert response.rankings[0].evaluation.final_score >= response.rankings[1].evaluation.final_score

    # Check that structured recency evidence is populated in API response
    cand_a_rec = response.rankings[0].evaluation.skill_recency_evidence
    assert len(cand_a_rec) > 0
    java_ev = next(e for e in cand_a_rec if e.skill == "Java")
    assert java_ev.found is True
    assert java_ev.used_in_current_role is True
    assert java_ev.freshness_score >= 90.0
