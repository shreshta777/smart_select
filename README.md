# SmartSelect

An explainable, recruiter-grade candidate shortlisting engine that evaluates and ranks resume batches against a Job Description using a combination of **fuzzy keyword matching** and **dense semantic embedding similarity**.

---

## Architecture Overview

```
                          ┌──────────────────────────┐
                          │   INPUT: JD & Resumes    │
                          │   (PDF Files / JSON)     │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │   PyMuPDF (fitz) Parser  │
                          │   & Robust Text Cleaner  │
                          └─────────────┬────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
            ┌─────────────────────────┐   ┌──────────────────────────┐
            │     Keyword Matcher     │   │     Semantic Matcher     │
            │  - RapidFuzz Aliases    │   │  - all-MiniLM-L6-v2      │
            │  - Required vs Preferred│   │  - Cosine Similarity     │
            │  - Coverage Breakdown   │   │  - Contextual Extraction │
            └────────────┬────────────┘   └────────────┬─────────────┘
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                          ┌──────────────────────────┐
                          │      Scoring Engine      │
                          │ Final = 0.5*KW + 0.5*Sem │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │      Ranking Engine      │
                          │  Strict Descending Order │
                          └─────────────┬────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
            ┌─────────────────────────┐   ┌──────────────────────────┐
            │   Top-3 Explanations    │   │   Why Candidate A over B │
            │   (Evidence-Backed)     │   │   (Comparative Analysis) │
            └────────────┬────────────┘   └────────────┬─────────────┘
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                          ┌──────────────────────────┐
                          │     FastAPI REST API     │
                          │ /health, /demo, /rank... │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │ Monochrome Recruiter UI  │
                          │  (Clean Enterprise View) │
                          └──────────────────────────┘
```

---

## Core Pillars

### 1. Robust PDF Parsing & Text Normalization (`backend/parser.py`, `backend/cleaner.py`)
- Uses **PyMuPDF (`fitz`)** for high-fidelity multi-page text extraction.
- Automatic section detection for `skills`, `experience`, `projects`, `education`, and `certifications` using regex heading patterns.
- Cleans extraction artifacts and page headers/numbers while strictly preserving critical engineering tokens (e.g. `Node.js`, `React.js`, `C++`, `C#`, `.NET`, `REST APIs`, `CI/CD`).

### 2. Fuzzy Keyword Matching (`backend/keyword_matcher.py`)
- Evaluates explicit requirements against candidate profiles.
- Canonical dictionary mapping and **RapidFuzz** token comparison ensure superficial formatting variations (`React` / `React.js` / `ReactJS`, `Node.js` / `NodeJS`, `MongoDB` / `Mongo DB`) are properly recognized.
- Strict weighting of **Required Skills** (70%) vs **Preferred Skills** (30%).

### 3. Dense Semantic Similarity (`backend/semantic_matcher.py`)
- Powered by `sentence-transformers` (`all-MiniLM-L6-v2`) and cosine similarity.
- Compares JD responsibilities and requirements with candidate work experience and projects.
- Contextually recognizes semantic equivalence without requiring exact keyword matches (e.g. "Develop RESTful APIs using Node.js" aligns strongly with "Built backend services using Express and MongoDB").

### 4. Transparent Score Combination (`backend/scorer.py`)
- Mathematical formula with no black-box LLM guessing:
  $$\text{KeywordScore} = 0.7 \times \text{ReqScore} + 0.3 \times \text{PrefScore}$$
  $$\text{FinalScore} = 0.5 \times \text{KeywordScore} + 0.5 \times \text{SemanticScore}$$
- Weights can be adjusted dynamically in the recruiter dashboard.

### 5. Deterministic Ranking & Top-3 Explanations (`backend/ranker.py`, `backend/explainer.py`)
- Full ranking of all candidates in descending order.
- Generates structured, evidence-backed justification for the top 3 candidates:
  - ✓ Matched required skills
  - ⚠ Missing skills
  - + Preferred skills
  - Practical semantic experience highlights
- **Comparative Analysis ("Why Candidate A over Candidate B?")**: side-by-side differentiators explaining why one candidate outranks another.
- **Job Description Bias & Narrow Constraint Audit**: detects institutional elitism, hyper-competitive gendered jargon, or unrealistic experience requirements for junior/intern roles.

---

## Repository Structure

```
nexora/
├── backend/
│   ├── main.py                  # FastAPI REST API application & static server
│   ├── models.py                # Pydantic schemas (JD, Resume, Scores, Explanations)
│   ├── parser.py                # PyMuPDF parser & section extractor
│   ├── cleaner.py               # Text cleaner preserving technical tokens
│   ├── keyword_matcher.py       # RapidFuzz fuzzy alias matching
│   ├── semantic_matcher.py      # all-MiniLM-L6-v2 embeddings + cosine similarity
│   ├── scorer.py                # Transparent score combination formula
│   ├── ranker.py                # Deterministic candidate ranking
│   ├── explainer.py             # Top-3 explanations, comparison, and JD bias audit
│   └── data/
│       ├── dummy_jd.json        # Junior Full Stack Developer Intern (TechNova Solutions)
│       └── dummy_resumes.json   # 18 realistic sample candidates with varying fits
├── frontend/
│   ├── index.html               # Recruiter dashboard (Pure monochrome aesthetic)
│   ├── styles.css               # Minimalist styling (black, white, greys only)
│   └── app.js                   # Interactive client-side controller
├── tests/
│   ├── test_parser.py           # Text cleaning, PDF extraction, section tests
│   ├── test_matcher.py          # Keyword & Semantic similarity tests (Express/Node.js sanity)
│   ├── test_scorer_ranker.py    # Score calculation & descending rank tests
│   ├── test_explainer.py        # Top-3 justification & A vs B comparison tests
│   └── test_api.py              # FastAPI endpoints integration tests
├── requirements.txt             # Dependencies
└── README.md                    # System documentation
```

---

## How to Run

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Run Test Suite
```powershell
python -m pytest tests/ -v
```

### 3. Launch the Backend & UI
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Access the Recruiter Dashboard
Open your web browser and navigate to:
```
http://localhost:8000
```

Click **"Run Demo Dataset"** to immediately evaluate and rank all 18 sample candidates with top-3 explanations, candidate details inspection, and side-by-side comparisons.

---

## API Endpoints

- `GET /health`: Health check (`{"status": "ok"}`)
- `GET /demo`: Runs the 18 sample resumes against the Junior Full Stack Developer Intern JD.
- `POST /rank`: Accepts uploaded JD PDF / text and multiple Resume PDFs.
- `POST /compare`: Accepts two candidate IDs and generates "Why Candidate A over Candidate B?" comparison.
- `POST /analyze-jd`: Inspects a Job Description for potential bias or overly narrow constraints.

---

## Replacing the Dummy Dataset with Real PDFs

When the final hackathon dataset is provided:
1. In the Web UI: Drag & drop the real **`Sample_JD.pdf`** into the Job Description dropzone, and select all **18 Resume PDFs** in the Batch Resumes dropzone. Click **`[ RANK CANDIDATES ]`**.
2. Alternatively via API / Python:
   ```python
   import requests

   files = [('resume_files', open(f'resume_{i}.pdf', 'rb')) for i in range(1, 19)]
   files.append(('jd_file', open('Sample_JD.pdf', 'rb')))
   
   response = requests.post('http://localhost:8000/rank', files=files)
   print(response.json())
   ```
The entire matching, scoring, ranking, explanation, and UI pipelines remain 100% identical.

---
