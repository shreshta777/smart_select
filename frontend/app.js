/**
 * InternLoom — Front-end Recruiter Dashboard Controller
 * RankForge AI Enterprise Edition
 */

let currentShortlistData = null;

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const btnRunDemo = document.getElementById("btn-run-demo");
  const btnHeroDemo = document.getElementById("btn-hero-demo");
  const btnRankCustom = document.getElementById("btn-rank-custom");
  const btnHeroUpload = document.getElementById("btn-hero-upload");
  const navBtnUpload = document.getElementById("nav-btn-upload");
  const navBrandLogo = document.getElementById("nav-brand-logo");
  const btnCheckBias = document.getElementById("btn-check-bias");
  const btnReEvalWeights = document.getElementById("btn-re-evaluate-weights");

  const jdFileInput = document.getElementById("jd-file-input");
  const resumesFileInput = document.getElementById("resumes-file-input");
  const jdFileStatus = document.getElementById("jd-file-status");
  const resumesFileStatus = document.getElementById("resumes-file-status");
  const loadingSpinner = document.getElementById("loading-spinner");
  
  const top3CardsContainer = document.getElementById("top-3-cards-container");
  const rankingsTableBody = document.getElementById("rankings-table-body");
  const candidateCountBadge = document.getElementById("candidate-count-badge");
  const jdBiasContainer = document.getElementById("jd-bias-container");
  
  const selectCandidateA = document.getElementById("select-candidate-a");
  const selectCandidateB = document.getElementById("select-candidate-b");
  const btnRunComparison = document.getElementById("btn-run-comparison");
  const comparisonResultArea = document.getElementById("comparison-result-area");
  const radarDisplayArea = document.getElementById("radar-display-area");

  const candidateModal = document.getElementById("candidate-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalBodyContent = document.getElementById("modal-body-content");

  const kwSlider = document.getElementById("kw-weight-slider");
  const semSlider = document.getElementById("sem-weight-slider");
  const kwVal = document.getElementById("kw-weight-val");
  const semVal = document.getElementById("sem-weight-val");

  const engineKwVal = document.getElementById("engine-kw-val");
  const engineSemVal = document.getElementById("engine-sem-val");
  const engineKwBar = document.getElementById("engine-kw-bar");
  const engineSemBar = document.getElementById("engine-sem-bar");

  // ==========================================
  // TAB NAVIGATION
  // ==========================================
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabViews = document.querySelectorAll(".tab-view");

  function switchTab(targetTabId) {
    navTabs.forEach(t => {
      if (t.getAttribute("data-tab") === targetTabId) {
        t.classList.add("active");
      } else {
        t.classList.remove("active");
      }
    });

    tabViews.forEach(v => {
      if (v.id === targetTabId) {
        v.classList.add("active");
      } else {
        v.classList.remove("active");
      }
    });
  }

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      switchTab(targetId);
    });
  });

  if (navBrandLogo) {
    navBrandLogo.addEventListener("click", () => switchTab("tab-home"));
  }

  function scrollToUploadSection() {
    switchTab("tab-home");
    const uploadSec = document.getElementById("upload-workspace-section");
    if (uploadSec) {
      uploadSec.scrollIntoView({ behavior: "smooth" });
    }
  }

  if (btnHeroUpload) {
    btnHeroUpload.addEventListener("click", scrollToUploadSection);
  }
  if (navBtnUpload) {
    navBtnUpload.addEventListener("click", scrollToUploadSection);
  }

  // ==========================================
  // WEIGHT CONTROLS SYNCHRONIZATION
  // ==========================================
  function updateWeightDisplays(val) {
    kwVal.textContent = val;
    semVal.textContent = 100 - val;
    if (engineKwVal) engineKwVal.textContent = `${val}%`;
    if (engineSemVal) engineSemVal.textContent = `${100 - val}%`;
    if (engineKwBar) engineKwBar.style.width = `${val}%`;
    if (engineSemBar) engineSemBar.style.width = `${100 - val}%`;
  }

  kwSlider.addEventListener("input", (e) => {
    const val = parseInt(e.target.value, 10);
    semSlider.value = 100 - val;
    updateWeightDisplays(val);
  });

  semSlider.addEventListener("input", (e) => {
    const val = parseInt(e.target.value, 10);
    kwSlider.value = 100 - val;
    updateWeightDisplays(100 - val);
  });

  if (btnReEvalWeights) {
    btnReEvalWeights.addEventListener("click", () => {
      if (!currentShortlistData) {
        alert("Please run evaluation or load the demo dataset first.");
        return;
      }
      recalculateWeightsLocally(parseInt(kwSlider.value, 10) / 100.0, parseInt(semSlider.value, 10) / 100.0);
    });
  }

  function recalculateWeightsLocally(kwWeight, semWeight) {
    if (!currentShortlistData || !currentShortlistData.rankings) return;
    
    // Recalculate combined scores deterministically
    currentShortlistData.rankings.forEach(r => {
      const kw = r.evaluation.keyword_score;
      const sem = r.evaluation.semantic_score;
      const final = (kwWeight * kw) + (semWeight * sem);
      r.evaluation.final_score = Math.round(final * 100) / 100;
    });

    // Re-sort strictly descending
    currentShortlistData.rankings.sort((a, b) => b.evaluation.final_score - a.evaluation.final_score);
    currentShortlistData.rankings.forEach((r, idx) => {
      r.rank = idx + 1;
    });

    renderAll(currentShortlistData);
    switchTab("tab-dashboard");
  }

  // File selection updates
  jdFileInput.addEventListener("change", () => {
    if (jdFileInput.files && jdFileInput.files[0]) {
      jdFileStatus.textContent = `Selected: ${jdFileInput.files[0].name}`;
    }
  });

  resumesFileInput.addEventListener("change", () => {
    if (resumesFileInput.files && resumesFileInput.files.length > 0) {
      resumesFileStatus.textContent = `Selected: ${resumesFileInput.files.length} resume file(s)`;
    }
  });

  // ==========================================
  // MULTI-STEP PIPELINE PROGRESS CONTROLLER
  // ==========================================
  const progressModalOverlay = document.getElementById("progress-modal-overlay");
  const progressPctVal = document.getElementById("progress-pct-val");
  const overallProgressFill = document.getElementById("overall-progress-fill");

  const PIPELINE_STEPS = [
    { id: "step-1", pct: 13, delay: 350 },
    { id: "step-2", pct: 25, delay: 400 },
    { id: "step-3", pct: 38, delay: 350 },
    { id: "step-4", pct: 52, delay: 450 },
    { id: "step-5", pct: 68, delay: 500 },
    { id: "step-6", pct: 80, delay: 350 },
    { id: "step-7", pct: 92, delay: 350 },
    { id: "step-8", pct: 100, delay: 400 },
  ];

  function resetProgressModal() {
    progressPctVal.textContent = "0%";
    overallProgressFill.style.width = "0%";
    PIPELINE_STEPS.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) {
        el.className = "pipeline-step-item pending";
      }
    });
  }

  function setStepState(stepId, state) {
    const el = document.getElementById(stepId);
    if (el) {
      el.className = `pipeline-step-item ${state}`;
    }
  }

  function setOverallProgress(pct) {
    progressPctVal.textContent = `${pct}%`;
    overallProgressFill.style.width = `${pct}%`;
  }

  async function executeWithStepProgress(fetchTaskPromise) {
    resetProgressModal();
    progressModalOverlay.classList.add("active");

    // Launch background fetch immediately
    const apiPromise = fetchTaskPromise();

    try {
      // Step sequentially through the 8 stages with visual active box and spinner
      for (let i = 0; i < PIPELINE_STEPS.length; i++) {
        const step = PIPELINE_STEPS[i];

        // Mark current step as active
        setStepState(step.id, "active");
        setOverallProgress(step.pct);

        // Await visual step progression duration
        await new Promise(r => setTimeout(r, step.delay));

        // Mark current step as completed with green check
        setStepState(step.id, "completed");
      }

      // Ensure API request is resolved
      const data = await apiPromise;
      currentShortlistData = data;

      // Small 400ms pause at 100% completion before switching to dashboard
      await new Promise(r => setTimeout(r, 400));
      progressModalOverlay.classList.remove("active");

      renderAll(data);
      switchTab("tab-dashboard");
    } catch (err) {
      progressModalOverlay.classList.remove("active");
      alert("Error during pipeline execution: " + (err.message || err));
    }
  }

  // ==========================================
  // DEMO RUNNER
  // ==========================================
  function executeDemo() {
    executeWithStepProgress(async () => {
      const res = await fetch("/demo");
      if (!res.ok) {
        const errDetail = await res.json().catch(() => ({}));
        throw new Error(errDetail.detail || "Failed to load demo dataset");
      }
      return await res.json();
    });
  }

  btnRunDemo.addEventListener("click", executeDemo);
  if (btnHeroDemo) {
    btnHeroDemo.addEventListener("click", executeDemo);
  }

  // ==========================================
  // REAL MULTI-FORMAT BATCH SHORTLISTING RUNNER
  // ==========================================
  btnRankCustom.addEventListener("click", () => {
    if (!jdFileInput.files || !jdFileInput.files[0]) {
      alert("Please upload a Job Description file (PDF, DOCX, TXT, or HTML) first.");
      return;
    }
    if (!resumesFileInput.files || resumesFileInput.files.length === 0) {
      alert("Please upload at least one Candidate Resume (PDF, DOCX, TXT, or HTML).");
      return;
    }

    const formData = new FormData();
    formData.append("jd_file", jdFileInput.files[0]);
    for (let i = 0; i < resumesFileInput.files.length; i++) {
      formData.append("resume_files", resumesFileInput.files[i]);
    }
    formData.append("keyword_weight", (parseInt(kwSlider.value, 10) / 100.0).toString());
    formData.append("semantic_weight", (parseInt(semSlider.value, 10) / 100.0).toString());

    executeWithStepProgress(async () => {
      const res = await fetch("/rank", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorDetail = await res.json().catch(() => ({}));
        throw new Error(errorDetail.detail || "Ranking failed");
      }

      return await res.json();
    });
  });

  // ==========================================
  // JD BIAS AUDIT
  // ==========================================
  btnCheckBias.addEventListener("click", async () => {
    try {
      showLoading(true);
      const formData = new FormData();
      if (jdFileInput.files[0]) {
        formData.append("jd_file", jdFileInput.files[0]);
      }
      const res = await fetch("/analyze-jd", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Could not analyze JD");
      const biasData = await res.json();
      renderJDBias(biasData);
      switchTab("tab-explainable");
    } catch (err) {
      alert("Error auditing JD: " + err.message);
    } finally {
      showLoading(false);
    }
  });

  // ==========================================
  // COMPARE CANDIDATES (WHY A OVER B?)
  // ==========================================
  btnRunComparison.addEventListener("click", async () => {
    const candAId = selectCandidateA.value;
    const candBId = selectCandidateB.value;
    if (!candAId || !candBId) return;

    try {
      const res = await fetch("/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_a_id: candAId,
          candidate_b_id: candBId,
        }),
      });
      if (!res.ok) throw new Error("Comparison failed");
      const compData = await res.json();
      renderComparisonResult(compData);
    } catch (err) {
      alert("Error running comparison: " + err.message);
    }
  });

  // Modal close handlers
  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", () => {
      if (candidateModal) candidateModal.classList.remove("active");
    });
  }
  window.addEventListener("click", (e) => {
    if (e.target === candidateModal) {
      candidateModal.classList.remove("active");
    }
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && candidateModal && candidateModal.classList.contains("active")) {
      candidateModal.classList.remove("active");
    }
  });

  function showLoading(show) {
    loadingSpinner.style.display = show ? "block" : "none";
  }

  // Chart instances for cleanup
  let skillsPieChartInstance = null;
  let cohortPieChartInstance = null;

  // ==========================================
  // TOP-3 CARDS RENDERER (ATS SCANNER CIRCULAR SCORE GAUGE)
  // ==========================================
  function renderTop3Cards(explanations) {
    top3CardsContainer.innerHTML = "";
    if (!explanations || explanations.length === 0) {
      top3CardsContainer.innerHTML = `<div class="empty-state-card"><p>No top candidate explanations available.</p></div>`;
      return;
    }

    explanations.forEach((exp) => {
      const card = document.createElement("div");
      card.className = "top-candidate-card";

      const matchedHtml = exp.matched_skills.map(s => `<span class="skill-pill matched">${escapeHtml(s)}</span>`).join(" ");
      const missingHtml = exp.missing_skills.map(s => `<span class="skill-pill missing">${escapeHtml(s)}</span>`).join(" ");
      const prefHtml = exp.matched_preferred.map(s => `<span class="skill-pill preferred">${escapeHtml(s)}</span>`).join(" ");
      const evidenceHtml = exp.semantic_evidence.map(e => `<li style="margin-bottom: 6px;">${escapeHtml(e)}</li>`).join("");

      // ATS Scanner Circular Gauge Calculations
      const radius = 30;
      const circumference = 2 * Math.PI * radius; // 188.495
      const scoreVal = Math.max(0, Math.min(100, exp.score));
      const strokeOffset = circumference - (scoreVal / 100) * circumference;
      const strokeColor = exp.rank === 1 ? '#F59E0B' : exp.rank === 2 ? '#2563EB' : '#7C3AED';
      const badgeStatus = scoreVal >= 75 ? 'Strong Shortlist' : scoreVal >= 40 ? 'High Potential' : 'Candidate Profile';

      card.innerHTML = `
        <div>
          <span class="rank-badge-large">Rank #${exp.rank}</span>
          <div class="top-candidate-name">${escapeHtml(exp.name)} <span style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);">(${exp.candidate_id})</span></div>
          
          <!-- ATS Scanner Circular Score Meter -->
          <div class="ats-scanner-gauge-box">
            <div class="ats-scanner-meta">
              <span class="ats-scanner-label">ATS SCANNER SCORE</span>
              <span class="ats-scanner-badge" style="color: ${strokeColor};">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                ${badgeStatus}
              </span>
            </div>
            <div class="ats-circle-gauge">
              <svg class="ats-circle-svg" viewBox="0 0 72 72">
                <circle class="ats-circle-bg" cx="36" cy="36" r="${radius}" />
                <circle class="ats-circle-fill" cx="36" cy="36" r="${radius}"
                  stroke-dasharray="${circumference.toFixed(2)}"
                  stroke-dashoffset="${strokeOffset.toFixed(2)}"
                  stroke="${strokeColor}" />
              </svg>
              <div class="ats-circle-center">
                <span class="ats-circle-score" style="color: ${strokeColor};">${exp.score.toFixed(1)}</span>
                <span class="ats-circle-sub">/ 100</span>
              </div>
            </div>
          </div>

          <div class="explanation-text">
            <strong>Why Ranked #${exp.rank}:</strong> ${escapeHtml(exp.why_ranked)}
          </div>

          ${evidenceHtml ? `
          <div style="margin-top: 14px; border-top: 1px solid var(--border-subtle); padding-top: 10px;">
            <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Semantic Alignment Evidence:</div>
            <ul style="font-size: 12px; padding-left: 18px; color: var(--text-secondary);">
              ${evidenceHtml}
            </ul>
          </div>
          ` : ''}
        </div>

        <button class="btn btn-secondary btn-sm" style="margin-top: 18px; width: 100%;" onclick="openCandidateModal('${exp.candidate_id}')">
          Inspect Candidate Profile
        </button>
      `;
      top3CardsContainer.appendChild(card);
    });
  }

  // ==========================================
  // RANKINGS TABLE RENDERER
  // ==========================================
  function renderRankingsTable(rankings) {
    rankingsTableBody.innerHTML = "";
    if (!rankings || rankings.length === 0) {
      rankingsTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 36px;">No candidates evaluated.</td></tr>`;
      return;
    }

    rankings.forEach((item) => {
      const evalItem = item.evaluation;
      const tr = document.createElement("tr");

      const rankBadge = item.rank <= 3
        ? `<span style="background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; padding: 2px 8px; border-radius: 6px; font-weight: 800;">#${item.rank}</span>`
        : `#${item.rank}`;

      tr.innerHTML = `
        <td class="rank-col">${rankBadge}</td>
        <td>
          <div style="font-weight: 800; color: var(--text-primary);">${escapeHtml(evalItem.name)}</div>
          <div style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">${evalItem.candidate_id}</div>
        </td>
        <td class="score-col">${evalItem.keyword_score.toFixed(1)}%</td>
        <td class="score-col">${evalItem.semantic_score.toFixed(1)}%</td>
        <td class="score-col" style="font-size: 15px; font-weight: 900; color: #2563EB;">${evalItem.final_score.toFixed(1)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openCandidateModal('${evalItem.candidate_id}')">Inspect</button>
        </td>
      `;
      rankingsTableBody.appendChild(tr);
    });
  }

  // ==========================================
  // COMPARISON SELECTS POPULATOR
  // ==========================================
  function populateComparisonSelects(rankings) {
    selectCandidateA.innerHTML = "";
    selectCandidateB.innerHTML = "";
    if (!rankings || rankings.length === 0) return;

    rankings.forEach((r, idx) => {
      const optA = document.createElement("option");
      optA.value = r.evaluation.candidate_id;
      optA.textContent = `#${r.rank} - ${r.evaluation.name} (${r.evaluation.final_score.toFixed(1)})`;
      if (idx === 0) optA.selected = true;
      selectCandidateA.appendChild(optA);

      const optB = document.createElement("option");
      optB.value = r.evaluation.candidate_id;
      optB.textContent = `#${r.rank} - ${r.evaluation.name} (${r.evaluation.final_score.toFixed(1)})`;
      if (idx === 1 || (idx === 0 && rankings.length === 1)) optB.selected = true;
      selectCandidateB.appendChild(optB);
    });
  }

  // ==========================================
  // COMPARISON RESULT CARD
  // ==========================================
  function renderComparisonResult(comp) {
    comparisonResultArea.style.display = "block";
    const cleanDiffs = comp.key_differentiators.filter(d => 
      !d.toLowerCase().includes("required skills") && 
      !d.toLowerCase().includes("req skills") &&
      !d.includes("0/0")
    );
    const diffList = cleanDiffs.map(d => `<li>${escapeHtml(d)}</li>`).join("");

    comparisonResultArea.innerHTML = `
      <div class="comparison-summary">
        ⭐ Advantage: ${escapeHtml(comp.higher_ranked_candidate)} (+${comp.score_delta.toFixed(1)} pts higher)
      </div>
      <p style="font-size: 13px; margin-bottom: 14px; color: var(--text-secondary); line-height: 1.55;">${escapeHtml(comp.summary)}</p>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; font-size: 13px; background: #F8FAFC; border: 1px solid var(--border-light); border-radius: 12px; padding: 14px;">
        <div>
          <strong style="color: var(--text-primary); font-size: 14px;">${escapeHtml(comp.candidate_a_name)}:</strong>
          <div style="margin-top: 4px;">Final Score: <strong style="color: #2563EB;">${comp.candidate_a_score.toFixed(1)}</strong></div>
          <div style="font-size: 12px; color: var(--text-secondary);">KW: ${comp.candidate_a_keyword.toFixed(1)}% | Sem: ${comp.candidate_a_semantic.toFixed(1)}%</div>
        </div>
        <div>
          <strong style="color: var(--text-primary); font-size: 14px;">${escapeHtml(comp.candidate_b_name)}:</strong>
          <div style="margin-top: 4px;">Final Score: <strong style="color: #2563EB;">${comp.candidate_b_score.toFixed(1)}</strong></div>
          <div style="font-size: 12px; color: var(--text-secondary);">KW: ${comp.candidate_b_keyword.toFixed(1)}% | Sem: ${comp.candidate_b_semantic.toFixed(1)}%</div>
        </div>
      </div>

      <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 6px;">Key Differentiators:</div>
      <ul class="differentiator-list">
        ${diffList}
      </ul>
    `;
  }

  // ==========================================
  // MASTER RENDER DISPATCHER
  // ==========================================
  function renderAll(data) {
    if (!data) return;
    currentShortlistData = data;
    window._LATEST_SHORTLIST_DATA = data;

    try {
      if (data.top_3_explanations) renderTop3Cards(data.top_3_explanations);
    } catch (err) {
      console.error("Error in renderTop3Cards:", err);
    }

    try {
      if (data.rankings) renderRankingsTable(data.rankings);
    } catch (err) {
      console.error("Error in renderRankingsTable:", err);
    }

    try {
      if (data.rankings) populateComparisonSelects(data.rankings);
    } catch (err) {
      console.error("Error in populateComparisonSelects:", err);
    }

    try {
      if (data.rankings) renderSkillRadar(data.rankings);
    } catch (err) {
      console.error("Error in renderSkillRadar:", err);
    }

    try {
      if (data.jd_analysis) renderJDBias(data.jd_analysis);
    } catch (err) {
      console.error("Error in renderJDBias:", err);
    }

    if (candidateCountBadge) {
      candidateCountBadge.textContent = data.total_candidates || (data.rankings ? data.rankings.length : 0);
    }
  }

  // ==========================================
  // SKILL RADAR / RECRUITER VISUALIZATIONS
  // ==========================================
  let requiredSkillsBarChartInstance = null;
  let scoreDistChartInstance = null;

  function renderSkillRadar(rankings) {
    if (!radarDisplayArea) return;
    if (!rankings || rankings.length === 0) {
      radarDisplayArea.innerHTML = `<div class="empty-state-card"><p>No candidate data available for skill analytics visualization.</p></div>`;
      return;
    }

    const totalCands = rankings.length;

    // 1. Collect all required skills & compute matched vs missing occurrences
    const requiredSkillMap = {};
    const missingSkillCounts = {};

    // Calculate score distribution into standard recruiter buckets: 90–100, 80–89, 70–79, 60–69, <60
    let bucket90_100 = 0;
    let bucket80_89 = 0;
    let bucket70_79 = 0;
    let bucket60_69 = 0;
    let bucketUnder60 = 0;

    rankings.forEach(r => {
      if (!r || !r.evaluation) return;
      const e = r.evaluation;
      const score = typeof e.final_score === 'number' ? e.final_score : 0;
      
      if (score >= 90) bucket90_100++;
      else if (score >= 80) bucket80_89++;
      else if (score >= 70) bucket70_79++;
      else if (score >= 60) bucket60_69++;
      else bucketUnder60++;

      const matchedReq = Array.isArray(e.matched_required_skills) ? e.matched_required_skills : [];
      const missingReq = Array.isArray(e.missing_required_skills) ? e.missing_required_skills : [];

      matchedReq.forEach(s => {
        if (!s) return;
        const norm = s.trim();
        if (!requiredSkillMap[norm]) requiredSkillMap[norm] = { matched: 0, missing: 0 };
        requiredSkillMap[norm].matched++;
      });

      missingReq.forEach(s => {
        if (!s) return;
        const norm = s.trim();
        if (!requiredSkillMap[norm]) requiredSkillMap[norm] = { matched: 0, missing: 0 };
        requiredSkillMap[norm].missing++;
        missingSkillCounts[norm] = (missingSkillCounts[norm] || 0) + 1;
      });
    });

    // Fallback if no required skills explicitly registered
    if (Object.keys(requiredSkillMap).length === 0) {
      rankings.forEach(r => {
        if (r && r.evaluation && Array.isArray(r.evaluation.skills)) {
          r.evaluation.skills.forEach(s => {
            if (!s) return;
            const norm = s.trim();
            if (!requiredSkillMap[norm]) requiredSkillMap[norm] = { matched: 0, missing: 0 };
            requiredSkillMap[norm].matched++;
          });
        }
      });
    }

    // Sort required skills by matched count descending
    const sortedRequiredSkills = Object.entries(requiredSkillMap)
      .map(([name, counts]) => {
        const matched = counts.matched;
        const pct = totalCands > 0 ? Math.round((matched / totalCands) * 100) : 0;
        return { name, matched, pct, missing: totalCands - matched };
      })
      .sort((a, b) => b.matched - a.matched || a.name.localeCompare(b.name));

    // Limit to top 10 required skills for chart presentation
    const chartSkills = sortedRequiredSkills.slice(0, 10);
    const skillLabels = chartSkills.map(s => s.name);
    const skillPercentages = chartSkills.map(s => s.pct);
    const skillMatchedCounts = chartSkills.map(s => s.matched);

    // Score distribution data
    const scoreBucketLabels = ['90–100', '80–89', '70–79', '60–69', '<60'];
    const scoreBucketCounts = [bucket90_100, bucket80_89, bucket70_79, bucket60_69, bucketUnder60];
    const scoreBucketPcts = scoreBucketCounts.map(c => totalCands > 0 ? Math.round((c / totalCands) * 100) : 0);

    // 3. Top Skill Gaps in Candidate Pool
    const sortedGaps = Object.entries(missingSkillCounts)
      .map(([skill, count]) => {
        const pct = totalCands > 0 ? Math.round((count / totalCands) * 100) : 0;
        let severity = 'low';
        let severityLabel = 'Minor Deficiency';
        let takeaway = 'Occasional gap across applicants.';
        if (pct >= 60) {
          severity = 'high';
          severityLabel = 'Critical Talent Shortage';
          takeaway = 'Most common technical deficiency across applicants.';
        } else if (pct >= 30) {
          severity = 'med';
          severityLabel = 'Moderate Gap';
          takeaway = 'Notable deficit in candidate pool; candidate upskilling recommended.';
        }
        return { skill, count, pct, severity, severityLabel, takeaway };
      })
      .sort((a, b) => b.count - a.count || b.pct - a.pct);

    // Build Top Skill Gaps HTML
    let gapsHtml = '';
    if (sortedGaps.length === 0) {
      gapsHtml = `
        <div class="skill-gap-empty">
          <div class="gap-check-icon">✓</div>
          <div>
            <strong>No Required Skill Gaps Detected</strong>
            <p>Every applicant in the current candidate pool satisfies all required technical criteria.</p>
          </div>
        </div>
      `;
    } else {
      gapsHtml = `
        <div class="skill-gaps-grid">
          ${sortedGaps.map(g => `
            <div class="skill-gap-card severity-${g.severity}">
              <div class="gap-card-header">
                <div class="gap-skill-name">${escapeHtml(g.skill)}</div>
                <span class="gap-severity-badge badge-${g.severity}">${g.severityLabel}</span>
              </div>
              <div class="gap-card-stats">
                <span class="gap-count-tag">Missing in <strong>${g.count}/${totalCands}</strong> candidates</span>
                <span class="gap-pct-tag">(${g.pct}%)</span>
              </div>
              <div class="gap-progress-bar">
                <div class="gap-progress-fill fill-${g.severity}" style="width: ${g.pct}%;"></div>
              </div>
              <div class="gap-takeaway">
                <span class="takeaway-bullet">&bull;</span> ${escapeHtml(g.takeaway)}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Build Main HTML Layout
    radarDisplayArea.innerHTML = `
      <div class="radar-charts-row">
        
        <!-- Left Chart: Required Skill Coverage Horizontal Bar Chart -->
        <div class="analytics-chart-card">
          <div class="analytics-chart-header">
            <div>
              <h4 class="analytics-chart-title">Required Skill Coverage Across Candidates</h4>
              <p class="analytics-chart-desc">Proportion and volume of applicants satisfying core JD qualifications (${totalCands} total candidates)</p>
            </div>
            <span class="analytics-chip-pill">Horizontal Coverage</span>
          </div>
          <div class="chart-canvas-box" style="height: 300px;">
            <canvas id="requiredSkillCoverageCanvas"></canvas>
          </div>
          <div class="skill-coverage-stats-list">
            ${chartSkills.map(s => `
              <div class="skill-stat-row">
                <div class="skill-stat-label">
                  <span class="skill-stat-name">${escapeHtml(s.name)}</span>
                  <span class="skill-stat-value">${s.matched}/${totalCands} <span class="skill-stat-pct">(${s.pct}%)</span></span>
                </div>
                <div class="skill-stat-track">
                  <div class="skill-stat-bar" style="width: ${s.pct}%;"></div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Right Chart: Candidate Score Distribution Bar Chart -->
        <div class="analytics-chart-card">
          <div class="analytics-chart-header">
            <div>
              <h4 class="analytics-chart-title">Candidate Score Distribution</h4>
              <p class="analytics-chart-desc">Spread of candidate final scores grouped into standard recruiter performance tiers</p>
            </div>
            <span class="analytics-chip-pill">Tier Spread</span>
          </div>
          <div class="chart-canvas-box" style="height: 300px;">
            <canvas id="scoreDistCanvas"></canvas>
          </div>
          <div class="tier-breakdown-legend">
            <div class="tier-legend-item">
              <span class="tier-legend-dot" style="background: #059669;"></span>
              <span><strong>90–100</strong> (Exceptional): <strong>${bucket90_100}</strong> candidates (${scoreBucketPcts[0]}%)</span>
            </div>
            <div class="tier-legend-item">
              <span class="tier-legend-dot" style="background: #2563EB;"></span>
              <span><strong>80–89</strong> (Strong): <strong>${bucket80_89}</strong> candidates (${scoreBucketPcts[1]}%)</span>
            </div>
            <div class="tier-legend-item">
              <span class="tier-legend-dot" style="background: #6366F1;"></span>
              <span><strong>70–79</strong> (Good Match): <strong>${bucket70_79}</strong> candidates (${scoreBucketPcts[2]}%)</span>
            </div>
            <div class="tier-legend-item">
              <span class="tier-legend-dot" style="background: #F59E0B;"></span>
              <span><strong>60–69</strong> (Developing): <strong>${bucket60_69}</strong> candidates (${scoreBucketPcts[3]}%)</span>
            </div>
            <div class="tier-legend-item">
              <span class="tier-legend-dot" style="background: #94A3B8;"></span>
              <span><strong>&lt;60</strong> (Needs Review): <strong>${bucketUnder60}</strong> candidates (${scoreBucketPcts[4]}%)</span>
            </div>
          </div>
        </div>

      </div>

      <!-- Section Below Charts: Top Skill Gaps in Candidate Pool -->
      <div class="top-gaps-section-card">
        <div class="top-gaps-header">
          <div>
            <h4 class="top-gaps-title">Top Skill Gaps in Candidate Pool</h4>
            <p class="top-gaps-desc">Most frequently missing required competencies across the applicant cohort with recruiter takeaways</p>
          </div>
          <span class="gaps-count-badge">${sortedGaps.length} Key Competency Gaps</span>
        </div>
        ${gapsHtml}
      </div>
    `;

    // Render Charts with Chart.js
    try {
      if (requiredSkillsBarChartInstance && typeof requiredSkillsBarChartInstance.destroy === 'function') {
        requiredSkillsBarChartInstance.destroy();
        requiredSkillsBarChartInstance = null;
      }
      if (scoreDistChartInstance && typeof scoreDistChartInstance.destroy === 'function') {
        scoreDistChartInstance.destroy();
        scoreDistChartInstance = null;
      }

      if (typeof Chart !== 'undefined') {
        // 1. Horizontal Bar Chart: Required Skill Coverage
        const ctxSkills = document.getElementById('requiredSkillCoverageCanvas');
        if (ctxSkills && skillLabels.length > 0) {
          const barColors = skillPercentages.map(pct => {
            if (pct >= 80) return 'rgba(37, 99, 235, 0.9)'; // Primary Blue
            if (pct >= 50) return 'rgba(79, 70, 229, 0.85)'; // Indigo
            if (pct >= 30) return 'rgba(245, 158, 11, 0.85)'; // Amber
            return 'rgba(239, 68, 68, 0.85)'; // Red
          });

          requiredSkillsBarChartInstance = new Chart(ctxSkills, {
            type: 'bar',
            data: {
              labels: skillLabels,
              datasets: [{
                label: 'Candidate Match Rate',
                data: skillPercentages,
                backgroundColor: barColors,
                borderRadius: 6,
                borderSkipped: false,
                barPercentage: 0.7,
                categoryPercentage: 0.85
              }]
            },
            options: {
              indexAxis: 'y',
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: '#1E293B',
                  titleFont: { family: 'Plus Jakarta Sans', size: 12, weight: '700' },
                  bodyFont: { family: 'Plus Jakarta Sans', size: 12 },
                  padding: 10,
                  cornerRadius: 8,
                  callbacks: {
                    label: function(context) {
                      const idx = context.dataIndex;
                      const cnt = skillMatchedCounts[idx];
                      const pct = skillPercentages[idx];
                      return ` Match: ${cnt}/${totalCands} candidates (${pct}%)`;
                    }
                  }
                }
              },
              scales: {
                x: {
                  min: 0,
                  max: 100,
                  grid: { color: '#F1F5F9' },
                  ticks: {
                    stepSize: 20,
                    callback: val => `${val}%`,
                    font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
                    color: '#64748B'
                  }
                },
                y: {
                  grid: { display: false },
                  ticks: {
                    font: { family: 'Plus Jakarta Sans', size: 12, weight: '700' },
                    color: '#1E293B'
                  }
                }
              }
            }
          });
        }

        // 2. Score Distribution Bar Chart
        const ctxScore = document.getElementById('scoreDistCanvas');
        if (ctxScore) {
          scoreDistChartInstance = new Chart(ctxScore, {
            type: 'bar',
            data: {
              labels: scoreBucketLabels,
              datasets: [{
                label: 'Candidate Count',
                data: scoreBucketCounts,
                backgroundColor: [
                  'rgba(5, 150, 105, 0.88)',  // 90-100 Emerald
                  'rgba(37, 99, 235, 0.88)',  // 80-89 Blue
                  'rgba(99, 102, 241, 0.88)', // 70-79 Indigo
                  'rgba(245, 158, 11, 0.88)', // 60-69 Amber
                  'rgba(148, 163, 184, 0.88)' // <60 Slate
                ],
                borderRadius: 6,
                borderSkipped: false,
                barPercentage: 0.65,
                categoryPercentage: 0.8
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: '#1E293B',
                  titleFont: { family: 'Plus Jakarta Sans', size: 12, weight: '700' },
                  bodyFont: { family: 'Plus Jakarta Sans', size: 12 },
                  padding: 10,
                  cornerRadius: 8,
                  callbacks: {
                    label: function(context) {
                      const idx = context.dataIndex;
                      const cnt = scoreBucketCounts[idx];
                      const pct = scoreBucketPcts[idx];
                      return ` ${cnt} candidate(s) (${pct}%)`;
                    }
                  }
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  grid: { color: '#F1F5F9' },
                  ticks: {
                    stepSize: 1,
                    precision: 0,
                    font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
                    color: '#64748B'
                  }
                },
                x: {
                  grid: { display: false },
                  ticks: {
                    font: { family: 'Plus Jakarta Sans', size: 12, weight: '700' },
                    color: '#1E293B'
                  }
                }
              }
            }
          });
        }
      }
    } catch (e) {
      console.warn("Chart rendering error:", e);
    }
  }

  // ==========================================
  // JD BIAS RENDERER
  // ==========================================
  function renderJDBias(analysis) {
    if (!analysis) return;
    jdBiasContainer.style.display = "block";

    if (analysis.has_flags) {
      const flagsHtml = analysis.flags.map(f => `
        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(245,158,11,0.25);">
          <strong>[${escapeHtml(f.category)}]</strong> "${escapeHtml(f.flagged_text)}"
          <div style="color: #78350F; margin-top: 2px;">${escapeHtml(f.explanation)}</div>
          <div style="margin-top: 3px; font-weight: 600;">✨ Recommendation: ${escapeHtml(f.recommendation)}</div>
        </div>
      `).join("");

      jdBiasContainer.innerHTML = `
        <div class="bias-alert-box">
          <strong style="font-size: 14px;">🛡 Job Description Inclusivity Audit: ${escapeHtml(analysis.summary)}</strong>
          ${flagsHtml}
        </div>
      `;
    } else {
      jdBiasContainer.innerHTML = `
        <div class="bias-alert-box" style="border-left-color: #10B981; background: #ECFDF5; border-color: #A7F3D0; color: #065F46;">
          <strong style="font-size: 14px;">🛡 Job Description Audit:</strong> ${escapeHtml(analysis.summary)}
        </div>
      `;
    }
  }

  // ==========================================
  // ==========================================
  // CANDIDATE PROFILE MODAL
  // ==========================================
  window.openCandidateModal = function(candidateId) {
    const data = currentShortlistData || window._LATEST_SHORTLIST_DATA;
    if (!data || !data.rankings) {
      console.warn("No shortlist data available to inspect candidate:", candidateId);
      return;
    }
    const cand = data.rankings.find(r => r && r.evaluation && r.evaluation.candidate_id === candidateId);
    if (!cand) {
      console.warn("Candidate not found in rankings:", candidateId);
      return;
    }

    const modalEl = candidateModal || document.getElementById("candidate-modal");
    const modalBodyEl = modalBodyContent || document.getElementById("modal-body-content");
    if (!modalEl || !modalBodyEl) {
      console.error("Candidate modal elements not found in DOM");
      return;
    }

    const evalItem = cand.evaluation || {};
    const skillsList = Array.isArray(evalItem.skills) ? evalItem.skills : [];
    const expList = Array.isArray(evalItem.experience) ? evalItem.experience : [];
    const projList = Array.isArray(evalItem.projects) ? evalItem.projects : [];
    const eduList = Array.isArray(evalItem.education) ? evalItem.education : [];
    const semanticMatchesList = Array.isArray(evalItem.key_semantic_matches) ? evalItem.key_semantic_matches : [];

    const skillsHtml = skillsList.map(s => `<span class="skill-pill">${escapeHtml(s)}</span>`).join(" ");
    const expHtml = expList.map(e => `<li>${escapeHtml(e)}</li>`).join("");
    const projHtml = projList.map(p => `<li>${escapeHtml(p)}</li>`).join("");
    const eduHtml = eduList.map(ed => `<li>${escapeHtml(ed)}</li>`).join("");

    const semanticMatchesHtml = semanticMatchesList.map(m => {
      const jdItem = m.jd_item || m.requirement || "Role Requirement";
      const candEv = m.candidate_evidence || m.evidence || "";
      const simScore = typeof m.similarity_score === "number" ? Math.round(m.similarity_score * 100) : null;
      return `
        <li style="margin-bottom: 8px;">
          <strong style="color: var(--text-primary);">${escapeHtml(jdItem)}:</strong>
          <div style="color: var(--text-secondary); margin-top: 2px;">${escapeHtml(candEv)}</div>
          ${simScore !== null ? `<span style="font-size: 10.5px; font-weight: 800; color: #059669; font-family: var(--font-mono);">Alignment Match: ${simScore}%</span>` : ''}
        </li>
      `;
    }).join("");

    // Extract skill analysis items or fallback to skill_recency_evidence
    const skillAnalysisList = Array.isArray(evalItem.skill_analysis) && evalItem.skill_analysis.length > 0 
      ? evalItem.skill_analysis 
      : (Array.isArray(evalItem.skill_recency_evidence) ? evalItem.skill_recency_evidence.map(r => ({
          skill: r.skill,
          matched: r.found,
          is_required: true,
          skill_score: r.freshness_score || 0,
          keyword_evidence: r.found ? 0.8 : 0.0,
          keyword_evidence_label: r.found ? "Strong" : "Missing",
          semantic_relevance: r.found ? 0.75 : 0.0,
          semantic_relevance_label: r.found ? "High" : "Low",
          freshness_score: r.freshness_score || 0,
          experience_alignment: r.used_in_current_role ? "Strong" : (r.experience_context === "project" ? "Moderate" : (r.found ? "Weak" : "None")),
          last_used: r.last_used,
          usage_context: r.experience_context,
          project_count: r.project_count || 0,
          action_verbs: [],
          evidence_snippets: [],
          explanation: `Context: ${r.experience_context}`
        })) : []);

    // Build PER-SKILL SCORE & MULTI-SIGNAL EVIDENCE Cards
    const perSkillCards = skillAnalysisList.map(item => {
      const itemScore = typeof item.skill_score === 'number' ? item.skill_score : 0;
      const scoreColor = itemScore >= 80 ? '#059669' : itemScore >= 60 ? '#2563EB' : itemScore >= 40 ? '#D97706' : '#94A3B8';
      const statusIcon = item.matched ? '✓ Matched' : '✕ Missing';
      const statusBg = item.matched ? '#ECFDF5' : '#FFF1F2';
      const statusBorder = item.matched ? '#A7F3D0' : '#FECDD3';
      const statusText = item.matched ? '#059669' : '#E11D48';

      const verbsBadges = item.action_verbs && item.action_verbs.length > 0 
        ? item.action_verbs.map(v => `<span style="background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; padding: 1px 6px; border-radius: 4px; font-size: 10.5px; font-weight: 700; margin-right: 4px;">${escapeHtml(v)}</span>`).join("")
        : '';

      const snippetsHtml = item.evidence_snippets && item.evidence_snippets.length > 0
        ? `<div style="margin-top: 6px; font-size: 11.5px; color: var(--text-secondary); background: #F8FAFC; border-left: 3px solid #CBD5E1; padding: 6px 10px; border-radius: 4px; line-height: 1.45;"><em>"${escapeHtml(item.evidence_snippets[0])}"</em></div>`
        : '';

      return `
        <div style="background: #FFFFFF; border: 1px solid var(--border-light); border-radius: 12px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <div>
                <strong style="font-size: 14.5px; color: var(--text-primary);">${escapeHtml(item.skill)}</strong>
                <div style="font-size: 10px; text-transform: uppercase; font-weight: 800; color: ${item.is_required ? '#2563EB' : '#7C3AED'}; margin-top: 1px;">
                  ${item.is_required ? 'Required Core Skill' : 'Preferred Bonus Skill'}
                </div>
              </div>
              <span style="background: ${statusBg}; color: ${statusText}; border: 1px solid ${statusBorder}; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 800;">
                ${statusIcon}
              </span>
            </div>

            <div style="margin-bottom: 10px;">
              <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 800; color: var(--text-secondary); margin-bottom: 3px;">
                <span>Skill Score:</span>
                <span style="color: ${scoreColor}; font-family: var(--font-mono); font-size: 13px;">${itemScore.toFixed(1)} / 100</span>
              </div>
              <div style="height: 6px; background: #EEF2F6; border-radius: 9999px; overflow: hidden;">
                <div style="height: 100%; width: ${Math.min(100, itemScore)}%; background: ${scoreColor}; border-radius: 9999px;"></div>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px; background: #F8FAFC; border: 1px solid var(--border-light); border-radius: 8px; padding: 8px; margin-bottom: 8px;">
              <div>
                <span style="color: var(--text-muted); font-weight: 700;">KW Evidence:</span>
                <strong style="color: var(--text-primary); margin-left: 2px;">${item.keyword_evidence_label || 'Missing'} (${((item.keyword_evidence || 0) * 100).toFixed(0)}%)</strong>
              </div>
              <div>
                <span style="color: var(--text-muted); font-weight: 700;">Semantic Rel:</span>
                <strong style="color: var(--text-primary); margin-left: 2px;">${item.semantic_relevance_label || 'Low'} (${((item.semantic_relevance || 0) * 100).toFixed(0)}%)</strong>
              </div>
            </div>

            ${verbsBadges ? `
            <div style="margin-bottom: 6px; font-size: 11px;">
              <span style="color: var(--text-muted); font-weight: 700;">Action Verbs:</span>
              <div style="display: inline-block; margin-left: 4px;">${verbsBadges}</div>
            </div>
            ` : ''}

            ${item.explanation ? `
            <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
              ${escapeHtml(item.explanation)}
            </div>
            ` : ''}

            ${snippetsHtml}
          </div>
        </div>
      `;
    }).join("");

    modalBodyEl.innerHTML = `
      <div style="border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px; margin-bottom: 20px;">
        <span class="rank-badge-large" style="background: var(--grad-primary);">Rank #${cand.rank}</span>
        <h2 style="font-size: 24px; font-weight: 800; margin-top: 6px; color: var(--text-primary);">${escapeHtml(evalItem.name)}</h2>
        <div style="font-size: 13px; color: var(--text-secondary); font-family: var(--font-mono);">Candidate ID: ${evalItem.candidate_id}</div>
      </div>

      <!-- 3 Score Metric Cards -->
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; background: #F8FAFC; border: 1px solid var(--border-light); border-radius: 12px; padding: 16px; margin-bottom: 22px;">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 800;">Final Score</div>
          <div style="font-size: 24px; font-weight: 900; font-family: var(--font-mono); color: #2563EB;">${(evalItem.final_score || 0).toFixed(1)}</div>
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; margin-top: 2px;">Composite Hybrid</div>
        </div>
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 800;">Keyword Score</div>
          <div style="font-size: 24px; font-weight: 900; font-family: var(--font-mono); color: #4F46E5;">${(evalItem.keyword_score || 0).toFixed(1)}%</div>
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; margin-top: 2px;">Evidence Weighted</div>
        </div>
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 800;">Semantic Score</div>
          <div style="font-size: 24px; font-weight: 900; font-family: var(--font-mono); color: #059669;">${(evalItem.semantic_score || 0).toFixed(1)}%</div>
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; margin-top: 2px;">Req &amp; Resp Vectors</div>
        </div>
      </div>

      <!-- SECTION: PER-SKILL SCORE & MULTI-SIGNAL BREAKDOWN -->
      <div style="margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div>
            <h4 style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: var(--text-primary); letter-spacing: 0.4px;">Per-Skill Evidence &amp; Scoring Breakdown</h4>
            <p style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Multi-vector transparent breakdown of keyword evidence, semantic relevance, and action verbs.</p>
          </div>
          <span style="font-size: 11px; font-weight: 800; background: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; padding: 2px 8px; border-radius: 6px;">Deterministic Metrics</span>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          ${perSkillCards}
        </div>
      </div>

      <!-- SECTION: EXTRACTED SKILLS -->
      <div style="margin-bottom: 18px;">
        <h4 style="font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; color: var(--text-secondary);">Skills Extracted from Resume</h4>
        <div class="skills-pill-group">${skillsHtml || '<em>No explicit skill list extracted</em>'}</div>
      </div>

      <!-- SECTION: EXPERIENCE -->
      <div style="margin-bottom: 18px;">
        <h4 style="font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; color: var(--text-secondary);">Work / Practical Experience</h4>
        <ul style="font-size: 13px; padding-left: 18px; color: var(--text-secondary); line-height: 1.55;">${expHtml || '<em>None listed</em>'}</ul>
      </div>

      <!-- SECTION: PROJECTS -->
      <div style="margin-bottom: 18px;">
        <h4 style="font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; color: var(--text-secondary);">Key Projects</h4>
        <ul style="font-size: 13px; padding-left: 18px; color: var(--text-secondary); line-height: 1.55;">${projHtml || '<em>None listed</em>'}</ul>
      </div>

      <!-- SECTION: EDUCATION -->
      <div style="margin-bottom: 18px;">
        <h4 style="font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; color: var(--text-secondary);">Education &amp; Academic Qualifications</h4>
        <ul style="font-size: 13px; padding-left: 18px; color: var(--text-secondary); line-height: 1.55;">${eduHtml || '<em>None listed</em>'}</ul>
      </div>

      <!-- SECTION: SEMANTIC MATCH EVIDENCE -->
      ${semanticMatchesHtml ? `
      <div style="margin-top: 20px; border-top: 1px solid var(--border-light); padding-top: 14px;">
        <h4 style="font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; color: var(--text-secondary);">Semantic Match Evidence Detail</h4>
        <ul style="font-size: 12px; padding-left: 18px; color: var(--text-secondary); line-height: 1.55;">${semanticMatchesHtml}</ul>
      </div>
      ` : ''}
    `;

    modalEl.classList.add("active");
  };

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")

      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});

