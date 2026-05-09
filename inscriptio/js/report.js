/* ============================================================
   inscriptio — report.js
   Logic for 04_hxai_report_view.html
   GET   /api/report/:reportId
   POST  /api/report/:reportId/validate
   PATCH /api/report/:reportId/notes
   POST  /api/report/:reportId/save
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', async () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  const reportId = sessionStorage.getItem('current_report_id');
  if (!reportId) {
    // Sidebar "Reports" can be opened without selecting a specific report.
    // In that case, keep the user on this page and show a clear empty state
    // rather than redirecting away.
    showToast('No report selected. Open a report from Dashboard or after Upload.', 'warning');

    const setText = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    setText('meta-name', 'Select a report');
    setText('meta-avatar', '–');
    const sid = document.getElementById('meta-student-id');
    const sclass = document.getElementById('meta-student-class');
    const sdate = document.getElementById('meta-date');
    const rid = document.getElementById('meta-report-id');
    if (sid) sid.innerHTML = '<em>ID</em> —';
    if (sclass) sclass.innerHTML = '<em>Class</em> —';
    if (sdate) sdate.innerHTML = '<em>Date</em> —';
    if (rid) rid.innerHTML = '<em>Report</em> —';

    setText('conf-value', '—');
    setText('conf-sub', '—');
    setText('meta-label', '—');
    setText('meta-confidence', '—');
    setText('meta-validated', '—');
    setText('conf-mid', '—');

    const confBar = document.getElementById('conf-bar-fill');
    if (confBar) confBar.style.width = '0%';

    const emptyPanel = (id, title) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:8px;padding:18px;text-align:center;">
          <div style="font-weight:700;color:var(--ink);font-size:0.95rem;">${title}</div>
          <div style="color:var(--ghost);font-size:0.82rem;line-height:1.5;">
            Pick a student from <strong>Dashboard → View Report</strong>, or run a new analysis from <strong>Upload</strong>.
          </div>
        </div>`;
    };
    emptyPanel('panel-original', 'No report loaded');
    emptyPanel('panel-shap', 'No SHAP map yet');
    emptyPanel('panel-gradcam', 'No Grad-CAM yet');

    // Disable actions that require a report
    const saveBtn = document.getElementById('save-btn');
    const discardBtn = document.getElementById('discard-btn');
    if (saveBtn) saveBtn.disabled = true;
    if (discardBtn) discardBtn.disabled = true;
    return;
  }

  // ── Role-based UI ─────────────────────────────────────────
  const isClinicianRole = user.role === 'clinician';
  const validationRow   = document.getElementById('validation-row');
  const clinicianLocked = document.getElementById('clinician-locked');

  if (validationRow && clinicianLocked) {
    validationRow.style.display   = isClinicianRole ? 'flex'  : 'none';
    clinicianLocked.style.display = isClinicianRole ? 'none'  : 'block';
  }

  // ── Load report data from backend ────────────────────────
  if (reportId) {
    try {
      const res  = await authFetch(`${API}/api/report/${reportId}`);
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Could not load report');

      const pct = data.softmax_score != null ? (data.softmax_score * 100) : null;
      const avgPD = data.avg_pd_prob != null ? data.avg_pd_prob : (pct ?? 0);

      // Exact match — "Low Potential" must NOT be caught by 'potential' check
      const isPotential = (data.label || '').trim().toLowerCase() === 'potential';

      // Top status flag
      const flag = document.getElementById('status-flag');
      if (flag) {
        flag.classList.toggle('potential', isPotential);
        flag.classList.toggle('low', !isPotential);
        flag.textContent = isPotential ? 'Potential Dysgraphia' : 'Low Potential';
      }

      // Meta header
      const metaName = document.getElementById('meta-name');
      const metaAvatar = document.getElementById('meta-avatar');
      const metaStudentId = document.getElementById('meta-student-id');
      const metaStudentClass = document.getElementById('meta-student-class');
      const metaDate = document.getElementById('meta-date');
      const metaReportId = document.getElementById('meta-report-id');

      if (metaName) metaName.textContent = data.student_name || '—';
      if (metaAvatar) {
        const nm = (data.student_name || '').trim();
        const initials = nm ? nm.split(/\s+/).slice(0, 2).map(p => p[0]?.toUpperCase() || '').join('') : '—';
        metaAvatar.textContent = initials || '—';
      }
      if (metaStudentId) metaStudentId.innerHTML = `<em>ID</em> #${data.student_id ?? '—'}`;
      if (metaStudentClass) metaStudentClass.innerHTML = `<em>Class</em> ${data.student_class || '—'}`;
      if (metaDate) metaDate.innerHTML = `<em>Date</em> ${data.created_at ? new Date(data.created_at).toLocaleDateString() : '—'}`;
      if (metaReportId) metaReportId.innerHTML = `<em>Report</em> #RPT-${String(data.report_id ?? reportId).padStart(4, '0')}`;

      // Confidence widgets
      const confValue = document.getElementById('conf-value');
      const confSub = document.getElementById('conf-sub');
      const metaLabel = document.getElementById('meta-label');
      const metaConfidence = document.getElementById('meta-confidence');
      const confMid = document.getElementById('conf-mid');
      const metaValidated = document.getElementById('meta-validated');

      if (confValue) {
        confValue.textContent = pct != null ? pct.toFixed(1) + '%' : '—';
        confValue.classList.toggle('high', isPotential);
        confValue.classList.toggle('low', !isPotential);
      }
      if (confSub) confSub.textContent = data.label || '—';
      if (metaLabel) {
        metaLabel.textContent = data.label || '—';
        metaLabel.style.color = isPotential ? 'var(--danger)' : 'var(--teal)';
      }
      if (metaConfidence) metaConfidence.textContent = pct != null ? pct.toFixed(1) + '%' : '—';
      if (confMid) confMid.textContent = pct != null ? pct.toFixed(1) + '%' : '—';
      if (metaValidated) {
        const v = data.verdict ? (data.verdict === 'verify' ? 'Verified' : 'Disagreed') : 'Pending';
        metaValidated.textContent = v;
        metaValidated.style.color = data.verdict ? 'var(--teal)' : 'var(--amber)';
      }

      // Confidence bar
     const confBar = document.getElementById('conf-bar-fill');
     if (confBar && pct != null) {
        confBar.style.width = pct.toFixed(1) + '%';
        confBar.style.backgroundColor = isPotential ? 'var(--danger)' : 'var(--teal)';
      }
      // Panel images — replace placeholders with real base64 images
      function setPanel(id, b64) {
        const el = document.getElementById(id);
        if (!el || !b64) return;
        el.innerHTML = `<img style="width:100%;height:100%;object-fit:contain;border-radius:8px;"
          src="data:image/png;base64,${b64}" alt="${id}">`;
      }

      setPanel('panel-original', data.original_b64);
      setPanel('panel-shap',     data.shap_b64);
      setPanel('panel-gradcam',  data.gradcam_b64);
      setPanel('panel-severe',   data.severe_anomaly_b64);

      // ── Probability Averaging section ──────────────────
      if (data.patch_breakdown && data.patch_breakdown.length > 0) {
        const section = document.getElementById('prob-averaging-section');
        const tbody   = document.getElementById('patch-tbody');
        const formula = document.getElementById('avg-formula');
        const diag    = document.getElementById('page-diagnosis');

        if (section) section.style.display = 'block';
        if (tbody) {
          tbody.innerHTML = '';
          data.patch_breakdown.forEach(p => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--rule)';
            const isPD = p.label.includes('PD') && !p.label.includes('LPD');
            tr.innerHTML = `
              <td style="padding:6px 8px;font-family:'DM Mono',monospace;">Patch ${p.patch_num}</td>
              <td style="padding:6px 8px;font-family:'DM Mono',monospace;">${p.pd_prob}%</td>
              <td style="padding:6px 8px;color:${isPD ? 'var(--danger)' : 'var(--teal)'};
                         font-weight:600;">${p.label}</td>
              <td style="padding:6px 8px;font-family:'DM Mono',monospace;">${p.confidence}%</td>`;
            tbody.appendChild(tr);
          });
        }
        if (formula) {
          const probs   = data.patch_breakdown.map(p => p.pd_prob);
          const avg     = (probs.reduce((a, b) => a + b, 0) / probs.length).toFixed(1);
          const formulaStr = probs.join(' + ');
          formula.innerHTML =
            `Mathematical Average: (${formulaStr}) / ${probs.length}<br>` +
            `<strong>Average PD Probability: ${avg}%</strong>`;
        }
        if (diag && avgPD != null) {
          // Show PD prob for Potential, Normal prob (100-PD) for Low Potential
          const diagPct   = isPotential ? avgPD.toFixed(1) : (100 - avgPD).toFixed(1);
          const diagColor = isPotential ? 'var(--danger)' : 'var(--teal)';
          const diagLabel = isPotential ? 'Potential Dysgraphia' : 'Low Potential';
          diag.innerHTML  = `▶ PAGE DIAGNOSIS: <span style="color:${diagColor};font-weight:700;">${diagLabel}</span> (${diagPct}% Overall System Confidence)`;
        }
      }

      // ── Evidence-Based Findings ────────────────────────
      if (data.findings) {
        const findingsSec  = document.getElementById('findings-section');
        const findingsBody = document.getElementById('findings-body');
        if (findingsSec)  findingsSec.style.display  = 'block';
        if (findingsBody) findingsBody.textContent = data.findings;
      }

      // ── PDF Download button ────────────────────────────
      const pdfBtn = document.getElementById('pdf-download-btn');
      if (pdfBtn) {
        pdfBtn.style.display = 'inline-flex';
        pdfBtn.addEventListener('click', async () => {
          pdfBtn.disabled    = true;
          pdfBtn.textContent = 'Generating PDF…';
          try {
            const r = await authFetch(`${API}/api/report/${reportId}/pdf`);
            if (!r.ok) throw new Error('PDF generation failed');
            const blob = await r.blob();
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href     = url;
            a.download = `inscriptio_report_RPT${String(reportId).padStart(4, '0')}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('PDF downloaded.', 'success');
          } catch {
            showToast('Could not generate PDF.', 'error');
          } finally {
            pdfBtn.disabled    = false;
            pdfBtn.textContent = '⬇ Download PDF Report';
          }
        });
      }

      // Pre-fill notes if already saved
      const notesField = document.getElementById('educator-notes');
      if (notesField && data.notes) notesField.value = data.notes;

      // Pre-fill verdict buttons if already validated
      if (data.verdict) {
        document.getElementById('val-verify')?.classList.toggle('selected',   data.verdict === 'verify');
        document.getElementById('val-disagree')?.classList.toggle('selected', data.verdict === 'disagree');
      }

    } catch (err) {
      showToast(`Could not load report: ${err.message}`, 'error');
    }
  }

  // ── Clinician validation ──────────────────────────────────
  let validationDecision = null;

  function setValidation(decision) {
    validationDecision = decision;
    document.getElementById('val-verify')?.classList.toggle('selected',   decision === 'verify');
    document.getElementById('val-disagree')?.classList.toggle('selected', decision === 'disagree');

    if (!reportId) { showToast('No report loaded.', 'warning'); return; }

    authFetch(`${API}/api/report/${reportId}/validate`, {
      method: 'POST',
      body:   JSON.stringify({ decision }),
    }).then(res => {
      if (res.ok) showToast(decision === 'verify' ? 'Marked as Verified.' : 'Marked as Disagreed.', 'info');
      else        showToast('Could not save validation.', 'error');
    }).catch(() => showToast('Could not save validation.', 'error'));
  }

  document.getElementById('val-verify')?.addEventListener('click',   () => setValidation('verify'));
  document.getElementById('val-disagree')?.addEventListener('click', () => setValidation('disagree'));

  // ── Notes autosave ────────────────────────────────────────
  const notesField = document.getElementById('educator-notes');
  let notesTimer   = null;

  notesField?.addEventListener('input', () => {
    clearTimeout(notesTimer);
    notesTimer = setTimeout(() => {
      if (!reportId) return;
      authFetch(`${API}/api/report/${reportId}/notes`, {
        method: 'PATCH',
        body:   JSON.stringify({ notes: notesField.value }),
      }).then(res => {
        if (res.ok) showToast('Note auto-saved.', 'info');
      });
    }, 2000);
  });

  // ── Save to history ───────────────────────────────────────
  document.getElementById('save-btn')?.addEventListener('click', async () => {
    if (isClinicianRole && !validationDecision) {
      showToast('Please select Verify or Disagree before saving.', 'warning'); return;
    }
    if (!reportId) { showToast('No report loaded.', 'warning'); return; }

    try {
      const res = await authFetch(`${API}/api/report/${reportId}/save`, {
        method: 'POST',
        body:   JSON.stringify({
          decision: validationDecision,
          notes:    notesField?.value || null,
        }),
      });
      if (!res.ok) throw new Error();
      showToast('Report saved to student history.', 'success');
      sessionStorage.removeItem('current_report_id');
      setTimeout(() => navigate('dashboard'), 1000);
    } catch {
      showToast('Could not save report.', 'error');
    }
  });

  // ── Discard ───────────────────────────────────────────────
  document.getElementById('discard-btn')?.addEventListener('click', () => {
    confirmModal(
      'This report and all notes will be discarded and will not be saved to the student\'s record.',
      () => {
        sessionStorage.removeItem('current_report_id');
        showToast('Report discarded.', 'warning');
        setTimeout(() => navigate('dashboard'), 800);
      }
    );
  });
});