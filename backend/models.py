"""Data models and schemas for InternLoom Smart Shortlisting Engine."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Resume(BaseModel):
    """Standardized representation of a candidate's resume."""
    candidate_id: str
    name: str = "Unknown Candidate"
    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    raw_text: str = ""


class JobDescription(BaseModel):
    """Standardized representation of a Job Description."""
    job_title: str = "Job Opening"
    company: Optional[str] = "Company"
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    description: str = ""
    raw_text: str = ""


class SkillMatchDetail(BaseModel):
    """Detailed evidence breakdown for an individual required or preferred skill."""
    skill: str
    is_required: bool = True
    strength: float = 0.0  # 0.0 = missing, 0.4 = skills list only, 0.7 = project, 1.0 = deep experience
    evidence_tier: str = "missing"  # deep_experience, project_evidence, skills_only, missing
    found_in_skills_list: bool = False
    found_in_experience: bool = False
    found_in_projects: bool = False
    in_current_role: bool = False
    usage_count: int = 0
    project_count: int = 0
    action_verbs: List[str] = Field(default_factory=list)
    evidence_snippets: List[str] = Field(default_factory=list)
    explanation: str = ""


class KeywordMatchResult(BaseModel):
    """Keyword match details for a candidate against a JD."""
    candidate_id: str
    matched_required_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    matched_preferred_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    required_skill_score: float = 0.0  # 0 to 100 (evidence-weighted)
    preferred_skill_score: float = 0.0  # 0 to 100 (evidence-weighted)
    keyword_score: float = 0.0  # 0 to 100
    evidence_depth_score: float = 0.0  # 0 to 100
    skill_match_details: List[SkillMatchDetail] = Field(default_factory=list)


class SemanticEvidenceItem(BaseModel):
    """Individual semantic alignment between JD item and resume section."""
    jd_item: str
    candidate_evidence: str
    similarity_score: float  # 0.0 to 1.0


class SemanticMatchResult(BaseModel):
    """Semantic match details for a candidate."""
    candidate_id: str
    semantic_score: float = 0.0  # 0 to 100
    experience_similarity: float = 0.0
    project_similarity: float = 0.0
    required_skills_semantic: float = 0.0
    responsibilities_semantic: float = 0.0
    key_semantic_matches: List[SemanticEvidenceItem] = Field(default_factory=list)


class SkillRecencyEvidence(BaseModel):
    """Structured evidence of how recently and in what context a skill was used."""
    skill: str
    found: bool = True
    last_used: Optional[int] = None
    used_in_current_role: bool = False
    project_count: int = 0
    experience_context: str = "unknown"  # current_role, work_experience, internship, project, college_project, certification, education, skills_section, missing, unknown
    freshness_score: float = 0.0


class RequiredSkillsSummary(BaseModel):
    """Structured summary of candidate's required skills match metrics."""
    total: int = 0
    matched_count: int = 0
    missing_count: int = 0
    match_percentage: float = 0.0
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class SkillAnalysisItem(BaseModel):
    """Comprehensive per-skill multi-signal analysis for dashboard and inspect view."""
    skill: str
    matched: bool = True
    is_required: bool = True
    skill_score: float = 0.0  # 0 to 100
    keyword_evidence: float = 0.0  # 0.0 to 1.0 (evidence strength)
    keyword_evidence_label: str = "Missing"  # Strong, Moderate, Weak, Missing
    semantic_relevance: float = 0.0  # 0.0 to 1.0
    semantic_relevance_label: str = "Low"  # High, Medium, Low
    freshness_score: float = 0.0  # 0 to 100
    experience_alignment: str = "None"  # Strong, Moderate, Weak, None
    last_used: Optional[int] = None
    usage_context: str = "missing"  # current_role, work_experience, internship, project, college_project, certification, skills_section, missing, unknown
    project_count: int = 0
    action_verbs: List[str] = Field(default_factory=list)
    evidence_snippets: List[str] = Field(default_factory=list)
    explanation: str = ""


class CandidateEvaluation(BaseModel):
    """Consolidated evaluation record for a candidate."""
    candidate_id: str
    name: str
    final_score: float
    keyword_score: float
    semantic_score: float
    recency_score: float = 0.0
    evidence_depth_score: float = 0.0
    required_skill_score: float
    preferred_skill_score: float
    matched_required_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    matched_preferred_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    required_skills_summary: RequiredSkillsSummary = Field(default_factory=RequiredSkillsSummary)
    skill_analysis: List[SkillAnalysisItem] = Field(default_factory=list)
    skill_match_details: List[SkillMatchDetail] = Field(default_factory=list)
    key_semantic_matches: List[SemanticEvidenceItem] = Field(default_factory=list)
    skill_recency_evidence: List[SkillRecencyEvidence] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)


class Top3Explanation(BaseModel):
    """Structured explanation for top-ranked candidates."""
    rank: int
    candidate_id: str
    name: str
    score: float
    keyword_score: float
    semantic_score: float
    recency_score: float = 0.0
    why_ranked: str
    matched_count: int = 0
    total_required: int = 0
    match_percentage: float = 0.0
    required_skills_summary: RequiredSkillsSummary = Field(default_factory=RequiredSkillsSummary)
    skill_analysis: List[SkillAnalysisItem] = Field(default_factory=list)
    matched_skills: List[str]
    missing_skills: List[str]
    matched_preferred: List[str]
    semantic_evidence: List[str]
    skill_recency_evidence: List[SkillRecencyEvidence] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    """Comparison between Candidate A and Candidate B."""
    candidate_a_id: str
    candidate_a_name: str
    candidate_a_score: float
    candidate_a_keyword: float
    candidate_a_semantic: float
    candidate_a_req_matched: int
    candidate_a_req_total: int
    candidate_a_missing: List[str]

    candidate_b_id: str
    candidate_b_name: str
    candidate_b_score: float
    candidate_b_keyword: float
    candidate_b_semantic: float
    candidate_b_req_matched: int
    candidate_b_req_total: int
    candidate_b_missing: List[str]

    higher_ranked_candidate: str
    score_delta: float
    summary: str
    key_differentiators: List[str]


class JDBiasItem(BaseModel):
    category: str
    flagged_text: str
    explanation: str
    recommendation: str


class JDBiasAnalysis(BaseModel):
    has_flags: bool
    summary: str
    flags: List[JDBiasItem] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    rank: int
    evaluation: CandidateEvaluation
    explanation: Optional[Top3Explanation] = None


class ShortlistResponse(BaseModel):
    job_title: str
    total_candidates: int
    weights: Dict[str, float]
    rankings: List[RankedCandidate]
    top_3_explanations: List[Top3Explanation]
    jd_analysis: Optional[JDBiasAnalysis] = None
