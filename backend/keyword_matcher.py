"""Keyword matching engine with RapidFuzz alias normalization and evidence-weighted depth scoring."""

import re
from typing import Dict, List, Set, Tuple, Optional, Any
from rapidfuzz import fuzz

from backend.models import KeywordMatchResult, SkillMatchDetail, Resume, JobDescription


# Normalized canonical mapping for common tech skill variations
CANONICAL_SKILL_MAP: Dict[str, List[str]] = {
    "react": ["react", "react.js", "reactjs", "react-js", "react native"],
    "node.js": ["node.js", "nodejs", "node js", "node"],
    "mongodb": ["mongodb", "mongo db", "mongo", "nosql document"],
    "javascript": ["javascript", "js", "ecmascript", "es6", "es6+"],
    "typescript": ["typescript", "ts"],
    "rest apis": ["rest apis", "rest api", "restful apis", "restful api", "restful web services", "rest", "restful", "json api", "api endpoints"],
    "docker": ["docker", "docker container", "containerization", "containers", "docker-compose", "containerized"],
    "aws": ["aws", "amazon web services", "amazon aws", "ec2", "s3", "lambda", "ecs", "cloud infrastructure"],
    "python": ["python", "python3", "py"],
    "postgresql": ["postgresql", "postgres", "postgre sql", "psql"],
    "mysql": ["mysql", "my sql", "mariadb"],
    "git": ["git", "github", "gitlab", "version control"],
    "html/css": ["html/css", "html", "css", "html5", "css3"],
    "express": ["express", "express.js", "expressjs"],
    "fastapi": ["fastapi", "fast api"],
    "graphql": ["graphql", "graph ql"],
    "tailwind": ["tailwind", "tailwindcss", "tailwind css"],
    "redux": ["redux", "redux toolkit", "rtk"],
    "next.js": ["next.js", "nextjs", "next js", "next"],
    "vue.js": ["vue.js", "vuejs", "vue"],
    "java": ["java", "core java", "j2ee"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp", ".net"],
}

# Substantive engineering/action verbs indicating practical depth
ACTION_VERBS: Set[str] = {
    "built", "developed", "deployed", "designed", "optimized", "engineered",
    "implemented", "created", "architected", "integrated", "maintained", "scaled",
    "automated", "tested", "configured", "authored", "structured", "refactored",
    "managed", "programmed", "orchestrated", "migrated", "debugged", "shipped"
}

CURRENT_ROLE_REGEX = re.compile(
    r"(?i)\b(present|current role|currently working|now|ongoing|date|2025|2026)\b"
)


def normalize_token(token: str) -> str:
    """Normalizes a single skill string for uniform comparison."""
    if not token:
        return ""
    token = token.lower().strip()
    token = re.sub(r"[\t\r\n]", " ", token)
    token = re.sub(r"\s+", " ", token)
    return token


def get_canonical_name(skill: str) -> str:
    """Finds canonical name if skill matches known aliases."""
    norm = normalize_token(skill)
    for canonical, aliases in CANONICAL_SKILL_MAP.items():
        if norm == canonical or norm in aliases:
            return canonical
        for alias in aliases:
            if fuzz.ratio(norm, alias) >= 90:
                return canonical
    return norm


def find_skill_occurrences_in_text(skill: str, text: str) -> bool:
    """Checks if a skill or its canonical aliases occurs in a specific text snippet."""
    if not text or not skill:
        return False

    norm_skill = normalize_token(skill)
    canon_skill = get_canonical_name(skill)
    text_lower = text.lower()

    aliases_to_check = [norm_skill]
    if canon_skill in CANONICAL_SKILL_MAP:
        aliases_to_check.extend(CANONICAL_SKILL_MAP[canon_skill])

    for alias in aliases_to_check:
        escaped_alias = re.escape(alias)
        if alias in ["c", "r"]:
            pattern = rf"(?:\b|(?<=[^a-zA-Z0-9])){escaped_alias}(?:\b|(?=[^a-zA-Z0-9]))"
        elif " " in alias or "." in alias or "+" in alias or "#" in alias or "/" in alias:
            pattern = rf"(?:\b|(?<=[^a-zA-Z0-9])){escaped_alias}(?:\b|(?=[^a-zA-Z0-9]))"
        else:
            pattern = rf"\b{escaped_alias}\b"

        if re.search(pattern, text_lower):
            return True

    # High fuzzy match threshold for compound phrases
    if len(norm_skill) > 5 and fuzz.partial_ratio(norm_skill, text_lower) >= 92:
        return True

# Backward-compatible alias
check_skill_in_corpus = find_skill_occurrences_in_text


def extract_skill_evidence_details(
    skill: str,
    resume: Resume,
    is_required: bool = True
) -> SkillMatchDetail:
    """Evaluates the depth, context, and quality of evidence behind a skill."""
    norm_skill = normalize_token(skill)
    canon_skill = get_canonical_name(skill)

    # 1. Check in explicit skills list
    in_skills_list = False
    for s in resume.skills:
        c_norm = normalize_token(s)
        c_canon = get_canonical_name(s)
        if norm_skill == c_norm or canon_skill == c_canon or (len(norm_skill) > 3 and fuzz.ratio(norm_skill, c_norm) >= 88):
            in_skills_list = True
            break

    # 2. Check in experience items
    matched_exp_snippets: List[str] = []
    in_current_role = False
    for exp in resume.experience:
        if find_skill_occurrences_in_text(skill, exp):
            matched_exp_snippets.append(exp.strip())
            if CURRENT_ROLE_REGEX.search(exp):
                in_current_role = True

    # 3. Check in project items
    matched_proj_snippets: List[str] = []
    for proj in resume.projects:
        if find_skill_occurrences_in_text(skill, proj):
            matched_proj_snippets.append(proj.strip())

    # 4. Check certifications / education
    has_cert = False
    for cert in resume.certifications:
        if find_skill_occurrences_in_text(skill, cert):
            has_cert = True
            break

    # 5. Fallback check on raw text if not yet found in structured lists
    raw_found = False
    if not (in_skills_list or matched_exp_snippets or matched_proj_snippets or has_cert):
        if find_skill_occurrences_in_text(skill, resume.raw_text):
            raw_found = True

    # Collect found action verbs across evidence snippets
    all_snippets = matched_exp_snippets + matched_proj_snippets
    found_verbs: Set[str] = set()
    for snip in all_snippets:
        words = re.findall(r"\b[a-zA-Z]+\b", snip.lower())
        for w in words:
            if w in ACTION_VERBS:
                found_verbs.add(w)

    usage_count = len(matched_exp_snippets) + len(matched_proj_snippets)
    project_count = len(matched_proj_snippets)
    has_exp = len(matched_exp_snippets) > 0
    has_proj = len(matched_proj_snippets) > 0

    # 6. Compute Evidence Strength (0.0 to 1.0)
    # Tier 0: Missing
    if not (in_skills_list or has_exp or has_proj or has_cert or raw_found):
        return SkillMatchDetail(
            skill=skill,
            is_required=is_required,
            strength=0.0,
            evidence_tier="missing",
            found_in_skills_list=False,
            found_in_experience=False,
            found_in_projects=False,
            in_current_role=False,
            usage_count=0,
            project_count=0,
            action_verbs=[],
            evidence_snippets=[],
            explanation=f"{skill} was not found in candidate profile."
        )

    # Tier 1: Deep Professional / Internship Experience (0.85 - 1.0)
    if has_exp:
        evidence_tier = "deep_experience"
        if in_current_role or (len(matched_exp_snippets) >= 2 and len(found_verbs) >= 2):
            strength = 1.0
            explanation = f"{skill} demonstrated with high production depth in current/recent role and practical workflows."
        elif len(matched_exp_snippets) >= 1 and has_proj:
            strength = 0.95
            explanation = f"{skill} demonstrated across professional experience and practical project implementations."
        elif len(found_verbs) >= 1:
            strength = 0.90
            explanation = f"{skill} verified in practical internship/work experience with concrete implementation."
        else:
            strength = 0.85
            explanation = f"{skill} mentioned in work experience context."

    # Tier 2: Practical Project Evidence (0.65 - 0.85)
    elif has_proj:
        evidence_tier = "project_evidence"
        if project_count >= 2 and len(found_verbs) >= 2:
            strength = 0.85
            explanation = f"{skill} actively demonstrated across {project_count} multi-tier projects."
        elif project_count >= 2 or len(found_verbs) >= 2:
            strength = 0.80
            explanation = f"{skill} demonstrated in {project_count} project(s) with functional engineering details."
        elif len(found_verbs) >= 1:
            strength = 0.75
            explanation = f"{skill} applied in project implementation: '{matched_proj_snippets[0][:60]}...'"
        else:
            strength = 0.70
            explanation = f"{skill} referenced in candidate project portfolio."

    # Tier 3: Skills List Only / Shallow Mention (0.40 - 0.50)
    else:
        evidence_tier = "skills_only"
        if has_cert:
            strength = 0.50
            explanation = f"{skill} listed in Skills section and verified via certification."
        elif in_skills_list:
            strength = 0.40
            explanation = f"{skill} was listed in the Skills section but lacked practical project or work experience."
        else:
            strength = 0.35
            explanation = f"{skill} was mentioned in resume text without dedicated project evidence."

    return SkillMatchDetail(
        skill=skill,
        is_required=is_required,
        strength=round(strength, 2),
        evidence_tier=evidence_tier,
        found_in_skills_list=in_skills_list,
        found_in_experience=has_exp,
        found_in_projects=has_proj,
        in_current_role=in_current_role,
        usage_count=usage_count,
        project_count=project_count,
        action_verbs=sorted(list(found_verbs)),
        evidence_snippets=all_snippets[:3],
        explanation=explanation
    )


def compute_evidence_depth_score(resume: Resume, skill_details: List[SkillMatchDetail]) -> float:
    """Computes an overall evidence depth score (0-100) based on substantive project/work evidence."""
    if not skill_details:
        return 0.0

    total_skills = len(skill_details)
    deep_count = sum(1 for d in skill_details if d.evidence_tier == "deep_experience")
    proj_count = sum(1 for d in skill_details if d.evidence_tier == "project_evidence")
    skills_only_count = sum(1 for d in skill_details if d.evidence_tier == "skills_only")

    # Ratio of practical evidence vs skills-only
    practical_ratio = (deep_count * 1.0 + proj_count * 0.75) / total_skills if total_skills > 0 else 0.0

    # Total projects & experience volume with action verbs
    exp_len = len(resume.experience)
    proj_len = len(resume.projects)
    volume_factor = min(1.0, (exp_len * 0.25 + proj_len * 0.20))

    depth_score = (0.70 * practical_ratio + 0.30 * volume_factor) * 100.0
    return round(min(100.0, max(0.0, depth_score)), 1)


def match_keywords(
    jd: JobDescription,
    resume: Resume,
    required_weight: float = 0.7,
    preferred_weight: float = 0.3
) -> KeywordMatchResult:
    """Evaluates candidate against JD using evidence-weighted multi-tier matching."""
    skill_details: List[SkillMatchDetail] = []
    matched_req: List[str] = []
    missing_req: List[str] = []
    req_strengths: List[float] = []

    # 1. Match Required Skills with Evidence Weights
    for req_skill in jd.required_skills:
        detail = extract_skill_evidence_details(req_skill, resume, is_required=True)
        skill_details.append(detail)
        req_strengths.append(detail.strength)

        # UI recognized match threshold (strength >= 0.35 means skill was at least stated)
        if detail.strength >= 0.35:
            matched_req.append(req_skill)
        else:
            missing_req.append(req_skill)

    total_req = len(jd.required_skills)
    req_score = (sum(req_strengths) / total_req * 100.0) if total_req > 0 else 100.0

    # 2. Match Preferred Skills with Evidence Weights
    matched_pref: List[str] = []
    missing_pref: List[str] = []
    pref_strengths: List[float] = []

    for pref_skill in jd.preferred_skills:
        detail = extract_skill_evidence_details(pref_skill, resume, is_required=False)
        skill_details.append(detail)
        pref_strengths.append(detail.strength)

        if detail.strength >= 0.35:
            matched_pref.append(pref_skill)
        else:
            missing_pref.append(pref_skill)

    total_pref = len(jd.preferred_skills)
    pref_score = (sum(pref_strengths) / total_pref * 100.0) if total_pref > 0 else 0.0

    # 3. Overall Evidence Depth Score
    evidence_depth = compute_evidence_depth_score(resume, skill_details)

    # 4. Calculate Combined Keyword Score (Weighted by Evidence Quality)
    if total_pref > 0:
        keyword_score = (required_weight * req_score) + (preferred_weight * pref_score)
    else:
        keyword_score = req_score

    return KeywordMatchResult(
        candidate_id=resume.candidate_id,
        matched_required_skills=matched_req,
        missing_required_skills=missing_req,
        matched_preferred_skills=matched_pref,
        missing_preferred_skills=missing_pref,
        required_skill_score=round(req_score, 1),
        preferred_skill_score=round(pref_score, 1),
        keyword_score=round(keyword_score, 1),
        evidence_depth_score=evidence_depth,
        skill_match_details=skill_details
    )
