"""Tests for keyword matching and semantic embedding matching engines."""

import pytest
from backend.models import Resume, JobDescription
from backend.keyword_matcher import match_keywords, check_skill_in_corpus
from backend.semantic_matcher import compute_semantic_match, encode_texts, get_embedding_model
from sklearn.metrics.pairwise import cosine_similarity


def test_keyword_matching_aliases():
    """Verifies that alias variations like ReactJS, NodeJS, Mongo DB are recognized."""
    jd = JobDescription(
        job_title="Full Stack Intern",
        required_skills=["JavaScript", "React", "Node.js", "MongoDB", "REST APIs"],
        preferred_skills=["Docker", "AWS"]
    )

    resume = Resume(
        candidate_id="C_TEST",
        name="Test Candidate",
        skills=["React.js", "NodeJS", "Mongo DB", "RESTful APIs", "AWS"],
        experience=["Engineered web apps with JavaScript"],
        projects=[],
        raw_text="Full stack engineer experienced in React.js, NodeJS, and Mongo DB."
    )

    res = match_keywords(jd, resume)
    assert "React" in res.matched_required_skills
    assert "Node.js" in res.matched_required_skills
    assert "MongoDB" in res.matched_required_skills
    assert "REST APIs" in res.matched_required_skills
    assert len(res.matched_required_skills) == 5
    assert res.required_skill_score > 0.0


def test_semantic_sanity_express_nodejs_match():
    """Sanity test required by problem statement:
    
    JD: "Develop RESTful APIs using Node.js."
    Resume: "Built backend services using Express and MongoDB."
    
    Verify that semantic matching identifies high meaningful similarity and clearly discriminates from unrelated text.
    """
    model = get_embedding_model()
    t1 = ["Develop RESTful APIs using Node.js."]
    t2 = ["Built backend services using Express and MongoDB."]
    unrelated = ["Bake chocolate chip cookies and desserts in the kitchen."]

    emb1 = encode_texts(t1, model=model)
    emb2 = encode_texts(t2, model=model)
    emb_unrelated = encode_texts(unrelated, model=model)

    sim = float(cosine_similarity(emb1, emb2)[0, 0])
    unrelated_sim = float(cosine_similarity(emb1, emb_unrelated)[0, 0])

    # Dense embeddings capture the strong semantic alignment
    assert sim >= 0.50, f"Expected semantic similarity >= 0.50, got {sim}"
    assert sim > (unrelated_sim + 0.35), f"Semantic match ({sim}) should far exceed unrelated baseline ({unrelated_sim})"


def test_semantic_pipeline_distinguishes_relevance():
    """Verifies that a relevant backend candidate scores much higher semantically than an embedded/hardware candidate."""
    jd = JobDescription(
        job_title="Junior Full Stack Developer Intern",
        required_skills=["JavaScript", "React", "Node.js", "MongoDB", "REST APIs"],
        responsibilities=[
            "Develop RESTful APIs using Node.js and integrate with frontend applications.",
            "Build responsive web interfaces using React."
        ]
    )

    strong_resume = Resume(
        candidate_id="STRONG",
        name="Strong Web Dev",
        experience=["Built scalable REST APIs and backend microservices with Express and NoSQL datastores."],
        projects=["Created single-page interactive web applications with modern component architectures."]
    )

    weak_resume = Resume(
        candidate_id="WEAK",
        name="Embedded Engineer",
        experience=["Programmed 8-bit microcontrollers in C for sensor acquisition."],
        projects=["Designed two-layer PCB schematics in KiCad for temperature sensors."]
    )

    strong_res = compute_semantic_match(jd, strong_resume)
    weak_res = compute_semantic_match(jd, weak_resume)

    assert strong_res.semantic_score > weak_res.semantic_score + 25.0
    assert len(strong_res.key_semantic_matches) > 0
