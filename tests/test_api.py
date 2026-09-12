"""Tests for FastAPI backend endpoints."""

import io
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_endpoint_returns_complete_rankings():
    response = client.get("/demo")
    assert response.status_code == 200
    data = response.json()
    assert "rankings" in data
    assert len(data["rankings"]) == 18
    assert "top_3_explanations" in data
    assert len(data["top_3_explanations"]) == 3
    # Check top candidate score
    top_cand = data["rankings"][0]
    assert top_cand["rank"] == 1
    assert top_cand["evaluation"]["final_score"] > 80.0


def test_compare_endpoint():
    # Trigger demo first to populate session
    client.get("/demo")
    payload = {
        "candidate_a_id": "C01",
        "candidate_b_id": "C02"
    }
    response = client.post("/compare", json=payload)
    assert response.status_code == 200
    comp = response.json()
    assert "higher_ranked_candidate" in comp
    assert "key_differentiators" in comp
    assert len(comp["key_differentiators"]) > 0


def test_rank_with_multipart_files():
    # Test uploading in-memory resume and JD text
    jd_content = "TechCorp\nJunior Developer\nRequired Skills:\nJavaScript, React, Node.js\nPreferred Skills:\nDocker"
    resume_content = "Alex Rivers\nSkills: React, JavaScript, Node.js\nExperience:\n- Built web apps in React."

    files = [
        ("resume_files", ("alex_resume.txt", io.BytesIO(resume_content.encode("utf-8")), "text/plain"))
    ]
    data = {
        "jd_text": jd_content
    }

    response = client.post("/rank", data=data, files=files)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["total_candidates"] == 1
    assert res_data["rankings"][0]["evaluation"]["candidate_id"] == "C01"
