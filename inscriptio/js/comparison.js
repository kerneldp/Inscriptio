/* ============================================================
   inscriptio — comparison.js
   Logic for 05_progress_comparison.html
   GET /api/students                      (populate dropdown)
   GET /api/students/:id/reports          (populate report selects)
   GET /api/students/:id/compare?r1=&r2=  (load dual panel)
   GET /api/students/:id/trend            (load line chart)
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', async () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  const studentSel = document.getElementById('student-select');
  const report1Sel = document.getElementById('date-select-1');
  const report2Sel = document.getElementById('date-select-2');
  const loadBtn    = document.getElementById('load-comparison-btn');

  const emptyState   = document.getElementById('empty-state');
  const compareWrap  = document.getElementById('comparison-container');
  const trendSection = document.getElementById('trend-section');

  // ── Populate student dropdown ─────────────────────────────
  async function loadStudents() {
    try {
      const res  = await authFetch(`${API}/api/students`);
      const data = await res.json();
      studentSel.innerHTML = '<option value="">— Select a student —</option>';
      (data.students || []).forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = `${s.name}${s.class ? ' · ' + s.class : ''}`;
        studentSel.appendChild(opt);
      });
    } catch { showToast('Could not load students.', 'error'); }
  }

  // ── Load report list for selected student ─────────────────
  async function loadReports(studentId) {
    report1Sel.innerHTML = '<option value="">— Select a date —</option>';
    report2Sel.innerHTML = '<option value="">— Select a date —</option>';
    report1Sel.disabled  = true;
    report2Sel.disabled  = true;
    loadBtn.disabled     = true;

    try {
      const res  = await authFetch(`${API}/api/students/${studentId}/reports`);
      const data = await res.json();

      if (!data.reports?.length) {
        showToast('No reports found for this student.', 'info'); return;
      }

      data.reports.forEach(r => {
        const date  = (r.session_date || r.created_at || '').split('T')[0] || '—';
        const score = r.softmax_score != null ? ` — ${(r.softmax_score * 100).toFixed(1)}%` : '';
        const label = r.label ? ` (${r.label})` : '';
        const text  = `${date}${score}${label}`;

        [report1Sel, report2Sel].forEach(sel => {
          const opt = document.createElement('option');
          opt.value = r.report_id;
          opt.textContent = text;
          sel.appendChild(opt);
        });
      });

      report1Sel.disabled = false;
      report2Sel.disabled = false;
      checkReady();

    } catch { showToast('Could not load reports.', 'error'); }
  }

  // ── Load comparison panels ────────────────────────────────
  async function loadComparison() {
    const studentId = studentSel.value;
    const r1        = report1Sel.value;
    const r2        = report2Sel.value;

    if (!studentId || !r1 || !r2) { showToast('Please select a student and two reports.', 'warning'); return; }
    if (r1 === r2)                 { showToast('Please select two different reports.', 'warning');     return; }

    loadBtn.disabled = true;
    loadBtn.textContent = 'Loading…';

    try {
      const res  = await authFetch(`${API}/api/students/${studentId}/compare?report1_id=${r1}&report2_id=${r2}&include_images=true`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Compare failed');

      renderPanel(1, data.report1);
      renderPanel(2, data.report2);

      if (compareWrap) compareWrap.style.display = 'block';
      if (trendSection) trendSection.style.display = 'block';
      if (emptyState) emptyState.style.display = 'none';

      await loadTrend(studentId);

    } catch (err) {
      showToast(`Could not load comparison: ${err.message}`, 'error');
    } finally {
      loadBtn.disabled    = false;
      loadBtn.textContent = 'Load Comparison';
    }
  }

  // ── Render a single comparison panel ─────────────────────
  function renderPanel(side, report) {
    const dateEl = document.getElementById(`panel-${side}-date`);
    const bodyEl = document.getElementById(`panel-${side}-content`);
    if (!dateEl || !bodyEl) return;

    const displayDate = (report.session_date || report.created_at || '').split('T')[0] || '—';
    dateEl.textContent = displayDate;

    const score     = report.softmax_score != null ? (report.softmax_score * 100).toFixed(1) : '—';
    const label     = report.label || '—';
    const statusCls = label === 'Potential' ? 'potential' : label === 'Low Potential' ? 'low' : 'pending';
    const barCls    = label === 'Potential' ? 'potential' : '';
    const verdictTxt = report.verdict
      ? `<span class="compare-meta-val" style="text-transform:capitalize">${report.verdict}</span>`
      : `<span class="compare-meta-val" style="color:var(--amber)">Pending</span>`;

    // 4-panel HXAI image grid
    const panels = [
      { key: 'original_b64',       label: '① Original' },
      { key: 'shap_b64',           label: '② SHAP' },
      { key: 'gradcam_b64',        label: '③ Grad-CAM' },
      { key: 'severe_anomaly_b64', label: '④ Severe Focus' },
    ];
    const panelCells = panels.map(p => !report[p.key] ? '' : `
      <div style="border:1px solid var(--rule);border-radius:8px;overflow:hidden;">
        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;color:var(--ghost);
                    padding:5px 8px;background:#fafaf8;border-bottom:1px solid var(--rule);">
          ${p.label}
        </div>
        <img src="data:image/png;base64,${report[p.key]}"
             style="width:100%;height:auto;display:block;" alt="${p.label}">
      </div>`).join('');

    const gridHtml = panelCells ? `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px;">
        ${panelCells}
      </div>` : '';

    bodyEl.innerHTML = `
      ${gridHtml}
      <div class="compare-score-row">
        <span class="compare-score-label">Confidence</span>
        <span class="compare-score-value ${statusCls}">${score}%</span>
      </div>
      <div class="compare-bar-wrap">
        <div class="compare-bar-fill ${barCls}" style="width:${score}%"></div>
      </div>
      <div class="compare-meta">
        <div class="compare-meta-row">
          <span class="compare-meta-key">Label</span>
          <span class="status-pill ${statusCls}">${label}</span>
        </div>
        <div class="compare-meta-row">
          <span class="compare-meta-key">Clinician verdict</span>
          ${verdictTxt}
        </div>
        ${report.notes ? `
        <div class="compare-meta-row" style="flex-direction:column;gap:4px;">
          <span class="compare-meta-key">Notes</span>
          <span class="compare-meta-val" style="font-size:0.8rem;line-height:1.5">${report.notes}</span>
        </div>` : ''}
      </div>`;
  }

  // ── Real trend chart ──────────────────────────────────────
  let trendChartInstance = null;

  async function loadTrend(studentId) {
    try {
      const res    = await authFetch(`${API}/api/students/${studentId}/trend`);
      const data   = await res.json();
      const points = data.points || [];

      const canvas   = document.getElementById('trend-chart');
      const emptyMsg = document.getElementById('trend-empty');

      if (points.length < 2) {
        if (canvas)   canvas.style.display  = 'none';
        if (emptyMsg) emptyMsg.style.display = 'block';
        return;
      }

      if (canvas)   canvas.style.display  = 'block';
      if (emptyMsg) emptyMsg.style.display = 'none';

      const labels = points.map(p => (p.session_date || p.created_at || '').split('T')[0]);
      const scores = points.map(p =>
        p.softmax_score != null ? parseFloat((p.softmax_score * 100).toFixed(1)) : null);

      if (trendChartInstance) { trendChartInstance.destroy(); trendChartInstance = null; }

      trendChartInstance = new Chart(canvas, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Confidence Score (%)',
              data: scores,
              borderColor: '#0e9fa0',
              backgroundColor: 'rgba(14,159,160,0.08)',
              borderWidth: 2.5,
              pointBackgroundColor: scores.map(s => s != null && s >= 80 ? '#c0392b' : '#0e9fa0'),
              pointRadius: 5,
              tension: 0.35,
              fill: true,
              spanGaps: true,
            },
            {
              label: 'Flagged Threshold (80%)',
              data: Array(labels.length).fill(80),
              borderColor: 'rgba(192,57,43,0.5)',
              borderDash: [6, 4],
              borderWidth: 1.5,
              pointRadius: 0,
              fill: false,
            }
          ]
        },
        options: {
          responsive: true,
          interaction: { intersect: false, mode: 'index' },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => {
                  if (ctx.datasetIndex === 1) return 'Threshold: 80%';
                  const pt = points[ctx.dataIndex];
                  return `Score: ${ctx.parsed.y}%  (${pt?.label || ''})`;
                },
                afterLabel: ctx => {
                  if (ctx.datasetIndex !== 0) return '';
                  const pt = points[ctx.dataIndex];
                  return pt?.verdict ? `Verdict: ${pt.verdict}` : '';
                }
              }
            }
          },
          scales: {
            y: {
              min: 0, max: 100,
              title: { display: true, text: 'Confidence Score (%)',
                       font: { family: 'DM Mono', size: 11 }, color: '#8a8f9a' },
              ticks: { font: { family: 'DM Mono', size: 10 }, color: '#8a8f9a' },
              grid: { color: '#ede8e0' }
            },
            x: {
              title: { display: true, text: 'Session Date',
                       font: { family: 'DM Mono', size: 11 }, color: '#8a8f9a' },
              ticks: { font: { family: 'DM Mono', size: 10 }, color: '#8a8f9a',
                       maxRotation: 35 },
              grid: { display: false }
            }
          }
        }
      });
    } catch (err) {
      console.error('Trend chart error:', err);
    }
  }


  studentSel?.addEventListener('change', () => {
    if (studentSel.value) loadReports(studentSel.value);
    else {
      report1Sel.innerHTML = '<option value="">— Select a date —</option>';
      report2Sel.innerHTML = '<option value="">— Select a date —</option>';
      report1Sel.disabled  = true;
      report2Sel.disabled  = true;
      loadBtn.disabled     = true;
      if (compareWrap) compareWrap.style.display = 'none';
      if (trendSection) trendSection.style.display = 'none';
      if (emptyState) emptyState.style.display = 'block';
    }
  });

  function checkReady() {
    loadBtn.disabled = !(studentSel.value && report1Sel.value && report2Sel.value);
  }
  report1Sel?.addEventListener('change', checkReady);
  report2Sel?.addEventListener('change', checkReady);
  loadBtn?.addEventListener('click', loadComparison);

  // ── Init ──────────────────────────────────────────────────
  await loadStudents();
});