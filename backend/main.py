"""FastAPI Application for InternLoom Smart Shortlisting Engine."""

import json
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.models import (
    JobDescription,
    Resume,
    CandidateEvaluation,
    RankedCandidate,
    Top3Explanation,
    ComparisonResult,
    JDBiasAnalysis,
    ShortlistResponse,
)
from backend.parser import parse_job_description, parse_resume, parse_pdf
from backend.keyword_matcher import match_keywords
from backend.semantic_matcher import compute_semantic_match, get_embedding_model
from backend.scorer import evaluate_candidate
from backend.recency import extract_candidate_skill_recency
from backend.ranker import rank_candidates
from backend.explainer import generate_top3_explanations, compare_candidates, analyze_jd_bias


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm embedding model on application launch."""
    get_embedding_model()
    yield


app = FastAPI(
    title="InternLoom Smart Shortlisting Engine",
    description="Deterministic keyword and semantic resume ranking for campus recruitment.",
    version="1.0.0",
    lifespan=lifespan
)


# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent / "data"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# In-memory storage for active run session (enables fast instant candidate comparison)
_ACTIVE_SESSION: Dict[str, Any] = {
    "jd": None,
    "evaluations": {},
    "response": None,
}


def run_pipeline(
    jd: JobDescription,
    resumes: List[Resume],
    keyword_weight: float = 0.5,
    semantic_weight: float = 0.5
) -> ShortlistResponse:
    """Executes the complete Shortlisting Engine pipeline."""
    evaluations: List[CandidateEvaluation] = []

    for resume in resumes:
        kw_result = match_keywords(jd, resume)
        sem_result = compute_semantic_match(jd, resume)
        rec_evidence, rec_score = extract_candidate_skill_recency(jd, resume)
        evaluation = evaluate_candidate(
            resume=resume,
            kw_result=kw_result,
            sem_result=sem_result,
            recency_score=rec_score,
            skill_recency_evidence=rec_evidence,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight
        )
        evaluations.append(evaluation)

    # Sort evaluations to find top 3
    evaluations_sorted = sorted(
        evaluations,
        key=lambda e: (e.final_score, e.required_skill_score, e.recency_score, e.semantic_score),
        reverse=True
    )

    top_3_explanations = generate_top3_explanations(evaluations_sorted, jd)
    top_3_map = {exp.candidate_id: exp for exp in top_3_explanations}

    ranked_candidates = rank_candidates(evaluations, top_3_map)
    jd_bias = analyze_jd_bias(jd)

    response = ShortlistResponse(
        job_title=jd.job_title,
        total_candidates=len(ranked_candidates),
        weights={"keyword_weight": keyword_weight, "semantic_weight": semantic_weight},
        rankings=ranked_candidates,
        top_3_explanations=top_3_explanations,
        jd_analysis=jd_bias
    )

    # Cache for live session comparison
    _ACTIVE_SESSION["jd"] = jd
    _ACTIVE_SESSION["evaluations"] = {e.candidate_id: e for e in evaluations}
    _ACTIVE_SESSION["response"] = response

    return response


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "InternLoom Smart Shortlisting Engine"}


@app.get("/demo", response_model=ShortlistResponse)
def run_demo():
    """Runs the full pipeline using the official dummy dataset (18 candidates + 1 JD)."""
    jd_path = DATA_DIR / "dummy_jd.json"
    resumes_path = DATA_DIR / "dummy_resumes.json"

    if not jd_path.exists() or not resumes_path.exists():
        raise HTTPException(status_code=500, detail="Dummy dataset files not found.")

    with open(jd_path, "r", encoding="utf-8") as f:
        jd_dict = json.load(f)
    with open(resumes_path, "r", encoding="utf-8") as f:
        resumes_dict = json.load(f)

    jd = JobDescription(**jd_dict)
    resumes = [Resume(**r) for r in resumes_dict]

    return run_pipeline(jd, resumes)


@app.post("/rank", response_model=ShortlistResponse)
async def rank_resumes(
    jd_file: Optional[UploadFile] = File(None),
    resume_files: Optional[List[UploadFile]] = File(None),
    jd_text: Optional[str] = Form(None),
    keyword_weight: float = Form(0.5),
    semantic_weight: float = Form(0.5)
):
    """Processes uploaded JD (PDF/DOCX/TXT/HTML) and Resume batch through the multi-format extraction pipeline."""
    # 1. Parse Job Description
    if jd_file is not None:
        jd_bytes = await jd_file.read()
        if not jd_bytes:
            raise HTTPException(status_code=400, detail="Uploaded Job Description file is empty.")
        try:
            jd = parse_job_description(
                jd_bytes,
                default_title="Full Stack Developer Intern",
                filename=jd_file.filename
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing Job Description ({jd_file.filename or 'file'}): {str(e)}"
            )
    elif jd_text and jd_text.strip():
        jd = parse_job_description(jd_text, default_title="Full Stack Developer Intern")
    else:
        raise HTTPException(
            status_code=400,
            detail="Missing Job Description. Please upload a Job Description file (PDF, DOCX, TXT, or HTML)."
        )

    # 2. Parse Uploaded Resumes
    if not resume_files or len(resume_files) == 0:
        raise HTTPException(
            status_code=400,
            detail="No Resume files uploaded. Please upload a batch of Resume files (PDF, DOCX, TXT, or HTML)."
        )

    resumes: List[Resume] = []
    errors: List[str] = []
    for idx, r_file in enumerate(resume_files, start=1):
        cand_id = f"C{idx:02d}"
        r_bytes = await r_file.read()
        if not r_bytes:
            errors.append(f"{r_file.filename}: file is empty")
            continue
        try:
            parsed_resume = parse_resume(r_bytes, candidate_id=cand_id, filename=r_file.filename)
            resumes.append(parsed_resume)
        except Exception as e:
            errors.append(f"{r_file.filename}: {str(e)}")

    if not resumes:
        detail_msg = "Could not extract text from the provided Resume files. Supported formats: PDF, DOCX, TXT, HTML."
        if errors:
            detail_msg += f" (Details: {'; '.join(errors)})"
        raise HTTPException(status_code=400, detail=detail_msg)

    return run_pipeline(jd, resumes, keyword_weight, semantic_weight)



@app.post("/compare", response_model=ComparisonResult)
def compare_candidates_endpoint(
    candidate_a_id: str = Body(..., embed=True),
    candidate_b_id: str = Body(..., embed=True)
):
    """Compares two candidates side-by-side: 'Why Candidate A over Candidate B?'"""
    eval_map = _ACTIVE_SESSION.get("evaluations", {})
    jd = _ACTIVE_SESSION.get("jd")

    # If session is empty, initialize demo
    if not eval_map or not jd:
        run_demo()
        eval_map = _ACTIVE_SESSION.get("evaluations", {})
        jd = _ACTIVE_SESSION.get("jd")

    cand_a = eval_map.get(candidate_a_id)
    cand_b = eval_map.get(candidate_b_id)

    if not cand_a:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_a_id}' not found in active session.")
    if not cand_b:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_b_id}' not found in active session.")

    return compare_candidates(cand_a, cand_b, jd)


@app.post("/analyze-jd", response_model=JDBiasAnalysis)
async def analyze_jd_endpoint(
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None)
):
    """Analyzes a Job Description for potential bias and overly restrictive constraints."""
    if jd_file:
        jd_bytes = await jd_file.read()
        jd = parse_job_description(jd_bytes, filename=jd_file.filename)
    elif jd_text:
        jd = parse_job_description(jd_text)
    elif _ACTIVE_SESSION.get("jd"):
        jd = _ACTIVE_SESSION["jd"]
    else:
        with open(DATA_DIR / "dummy_jd.json", "r", encoding="utf-8") as f:
            jd = JobDescription(**json.load(f))

    return analyze_jd_bias(jd)



# Serve frontend static assets if available
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def serve_frontend_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        return "<h1>InternLoom Engine Ready. Frontend index.html not found.</h1>"
