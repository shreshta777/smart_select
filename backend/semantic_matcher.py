"""Semantic matching engine using Sentence Transformers and cosine similarity."""

import logging
from typing import List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from backend.models import SemanticEvidenceItem, SemanticMatchResult, Resume, JobDescription

logger = logging.getLogger(__name__)

# Global model singleton
_EMBEDDING_MODEL = None
MODEL_NAME = "all-MiniLM-L6-v2"


def get_embedding_model():
    """Loads and caches the SentenceTransformer model."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model '{MODEL_NAME}'...")
            _EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME)
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer '{MODEL_NAME}': {e}. Using TF-IDF fallback.")
            _EMBEDDING_MODEL = "TFIDF_FALLBACK"
    return _EMBEDDING_MODEL


def encode_texts(texts: List[str], model=None) -> np.ndarray:
    """Generates normalized vector embeddings for a list of text strings."""
    if not texts:
        return np.empty((0, 384))

    if model is None:
        model = get_embedding_model()

    if model != "TFIDF_FALLBACK":
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        return embeddings
    else:
        # Graceful TF-IDF fallback if sentence-transformers is unavailable
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(ngram_range=(1, 2))
        return vec.fit_transform(texts).toarray()


def compute_semantic_match(
    jd: JobDescription,
    resume: Resume,
    top_k_evidence: int = 3
) -> SemanticMatchResult:
    """Calculates requirement-level and holistic semantic similarity between JD and Resume content."""
    model = get_embedding_model()

    # 1. Compile JD semantic target categories
    jd_req_targets: List[str] = [f"Hands-on proficiency and engineering with {req}" for req in jd.required_skills if req.strip()]
    jd_resp_targets: List[str] = [resp.strip() for resp in jd.responsibilities if resp.strip()]
    jd_pref_targets: List[str] = [f"Practical experience with {pref}" for pref in jd.preferred_skills if pref.strip()]

    # Holistic JD target list
    jd_all_targets: List[str] = []
    jd_all_targets.extend(jd_resp_targets)
    jd_all_targets.extend(jd_req_targets)
    jd_all_targets.extend(jd_pref_targets)

    if not jd_all_targets and jd.description:
        jd_all_targets = [line.strip() for line in jd.description.split("\n") if len(line.strip()) > 15]

    if not jd_all_targets:
        jd_all_targets = ["Full stack software engineering and web application development."]

    # 2. Compile Candidate semantic evidence units by section
    exp_items: List[str] = [exp.strip() for exp in resume.experience if exp.strip()]
    proj_items: List[str] = [proj.strip() for proj in resume.projects if proj.strip()]
    
    # Practical evidence (experience + projects) is prioritized for semantic depth
    practical_items: List[str] = exp_items + proj_items
    
    candidate_all_items: List[str] = list(practical_items)
    if resume.skills:
        candidate_all_items.append("Technical Skills: " + ", ".join(resume.skills))

    if not candidate_all_items and resume.raw_text:
        candidate_all_items = [line.strip() for line in resume.raw_text.split("\n") if len(line.strip()) > 15]

    if not candidate_all_items:
        return SemanticMatchResult(
            candidate_id=resume.candidate_id,
            semantic_score=0.0,
            experience_similarity=0.0,
            project_similarity=0.0,
            required_skills_semantic=0.0,
            responsibilities_semantic=0.0,
            key_semantic_matches=[]
        )

    # 3. Compute dense vector embeddings
    jd_embeddings = encode_texts(jd_all_targets, model=model)
    cand_embeddings = encode_texts(candidate_all_items, model=model)

    if jd_embeddings.shape[0] == 0 or cand_embeddings.shape[0] == 0:
        return SemanticMatchResult(
            candidate_id=resume.candidate_id,
            semantic_score=0.0,
            experience_similarity=0.0,
            project_similarity=0.0,
            required_skills_semantic=0.0,
            responsibilities_semantic=0.0,
            key_semantic_matches=[]
        )

    # 4. Compute cosine similarity matrix (shape: len(jd_all_targets) x len(candidate_all_items))
    if model != "TFIDF_FALLBACK":
        sim_matrix = np.dot(jd_embeddings, cand_embeddings.T)
    else:
        from sklearn.metrics.pairwise import cosine_similarity as cos_sim
        sim_matrix = cos_sim(jd_embeddings, cand_embeddings)

    # Section index bounds
    resp_len = len(jd_resp_targets)
    req_len = len(jd_req_targets)
    exp_len = len(exp_items)
    proj_len = len(proj_items)
    pract_len = len(practical_items)

    # 4a. Requirement-level semantic alignment (JD required competencies against candidate practical items)
    req_sem_score = 0.0
    if req_len > 0:
        req_sub_matrix = sim_matrix[resp_len:resp_len + req_len, :]
        if pract_len > 0:
            # Check maximum match against candidate's practical experience & projects
            pract_sub = req_sub_matrix[:, :pract_len]
            req_sem_score = float(np.mean(np.max(pract_sub, axis=1))) * 100.0
        else:
            req_sem_score = float(np.mean(np.max(req_sub_matrix, axis=1))) * 100.0

    # 4b. Responsibilities semantic alignment
    resp_sem_score = 0.0
    if resp_len > 0:
        resp_sub_matrix = sim_matrix[:resp_len, :]
        if pract_len > 0:
            pract_sub = resp_sub_matrix[:, :pract_len]
            resp_sem_score = float(np.mean(np.max(pract_sub, axis=1))) * 100.0
        else:
            resp_sem_score = float(np.mean(np.max(resp_sub_matrix, axis=1))) * 100.0

    # 4c. Sub-section similarities (Experience and Projects)
    exp_sim = 0.0
    if exp_len > 0:
        exp_matrix = sim_matrix[:, :exp_len]
        exp_sim = float(np.mean(np.max(exp_matrix, axis=1))) * 100.0

    proj_sim = 0.0
    if proj_len > 0:
        proj_matrix = sim_matrix[:, exp_len:exp_len + proj_len]
        proj_sim = float(np.mean(np.max(proj_matrix, axis=1))) * 100.0

    # 4d. Combined holistic semantic score
    # Emphasize practical context over mere keyword enumeration
    max_per_target = np.max(sim_matrix, axis=1)
    sorted_scores = np.sort(max_per_target)[::-1]
    top_subset_len = max(1, int(np.ceil(len(sorted_scores) * 0.8)))
    holistic_score = float(np.mean(sorted_scores[:top_subset_len])) * 100.0

    if req_sem_score > 0 and resp_sem_score > 0:
        semantic_score = (0.50 * holistic_score) + (0.30 * req_sem_score) + (0.20 * resp_sem_score)
    elif req_sem_score > 0:
        semantic_score = (0.60 * holistic_score) + (0.40 * req_sem_score)
    else:
        semantic_score = holistic_score

    semantic_score = float(np.clip(semantic_score, 0.0, 100.0))

    # 5. Extract top-K semantic evidence pairs (focus on practical items)
    evidence_pairs: List[Tuple[float, str, str]] = []
    for i, jd_item in enumerate(jd_all_targets):
        for j, cand_item in enumerate(candidate_all_items):
            sim = float(sim_matrix[i, j])
            # Boost score slightly if evidence comes from practical experience/projects
            is_practical = j < pract_len
            effective_sim = sim if is_practical else sim * 0.85
            evidence_pairs.append((effective_sim, jd_item, cand_item))

    evidence_pairs.sort(key=lambda x: x[0], reverse=True)

    seen_cand = set()
    top_evidence_items: List[SemanticEvidenceItem] = []
    for sim, jd_t, cand_t in evidence_pairs:
        if cand_t not in seen_cand and sim > 0.35:
            seen_cand.add(cand_t)
            top_evidence_items.append(
                SemanticEvidenceItem(
                    jd_item=jd_t,
                    candidate_evidence=cand_t,
                    similarity_score=round(sim, 3)
                )
            )
            if len(top_evidence_items) >= top_k_evidence:
                break

    return SemanticMatchResult(
        candidate_id=resume.candidate_id,
        semantic_score=round(semantic_score, 1),
        experience_similarity=round(exp_sim, 1),
        project_similarity=round(proj_sim, 1),
        required_skills_semantic=round(req_sem_score, 1),
        responsibilities_semantic=round(resp_sem_score, 1),
        key_semantic_matches=top_evidence_items
    )
