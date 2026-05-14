/* ============================================================
   inscriptio — clinician.js
   Two-column HITL workspace — GET /api/clinician/queue
   GET /api/clinician/validated  GET /api/report/{id}
   POST /api/clinician/report/{id}/adjudicate
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', async () => {
  const user = Session.require();
  if (!user || user.role !== 'clinician') {
    showToast('This workspace is for clinicians only.', 'warning');
    setTimeout(() => navigate('dashboard'), 400);
    return;
  }

  const el = (id) => document.getElementById(id);
  let queue = [];
  let validatedList = [];
  let listMode = 'pending'; // 'pending' | 'validated'
  let activeReportId = null;
  let selectedVerdict = null;

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  el('clin-avatar').textContent = user.initials || '—';
  el('clin-name').textContent   = user.name || 'Clinician';
  el('clin-logout').addEventListener('click', () => {
    Session.clear();
    navigate('auth');
  });

  function setEmptyCopy() {
    const t = el('clin-empty-text');
    if (!t) return;
    if (listMode === 'pending') {
      t.textContent = 'Choose a student card on the left to load XAI evidence and adjudicate.';
    } else {
      t.textContent = 'Choose a validated report on the left to browse XAI evidence and read-only adjudication details.';
    }
  }

  function setMasterHeader() {
    const title = el('clin-master-title');
    const desc = el('clin-master-desc');
    if (!title || !desc) return;
    if (listMode === 'pending') {
      title.textContent = 'Pending queue';
      desc.textContent = 'Sorted by urgency, clinical severity (≥80%), score, then receipt order.';
    } else {
      title.textContent = 'Validated reports';
      desc.textContent = 'Closed cases—review XAI panels and adjudication details (read-only).';
    }
  }

  function updateTabs() {
    const p = el('clin-tab-pending');
    const v = el('clin-tab-validated');
    if (p) {
      p.classList.toggle('is-active', listMode === 'pending');
      p.setAttribute('aria-selected', listMode === 'pending');
    }
    if (v) {
      v.classList.toggle('is-active', listMode === 'validated');
      v.setAttribute('aria-selected', listMode === 'validated');
    }
  }

  function badgeClass(b) {
    if (b === 'validated') return 'clin-pill-validated';
    if (b === 'followup') return 'clin-pill-followup';
    return 'clin-pill-pending';
  }

  function badgeLabel(b) {
    if (b === 'validated') return 'Validated';
    if (b === 'followup') return 'Requires follow-up';
    return 'Pending review';
  }

  function currentList() {
    return listMode === 'pending' ? queue : validatedList;
  }

  function renderList() {
    const mount = el('clin-queue-list');
    if (!mount) return;
    const items = currentList();
    if (!items.length) {
      mount.innerHTML = listMode === 'pending'
        ? '<div class="clin-queue-empty">No screenings awaiting validation.</div>'
        : '<div class="clin-queue-empty">No validated reports yet.</div>';
      return;
    }
    mount.innerHTML = items.map(item => {
      const dt = item.created_at ? item.created_at.split('T')[0] : '—';
      const priority = listMode === 'pending' && (item.urgent_review || (item.clinical_severity != null && item.clinical_severity >= 0.8));
      const prClass = priority ? 'is-priority' : '';
      const active = item.report_id === activeReportId ? 'is-active' : '';
      return `
        <button type="button" class="clin-queue-card ${prClass} ${active}" data-report-id="${item.report_id}">
          <div class="clin-queue-card-inner">
            <div class="clin-queue-avatar">${escapeHtml(item.student_initials)}</div>
            <div class="clin-queue-body">
              <div class="clin-queue-id">STU-${String(item.student_id).padStart(3, '0')} · Upload ${escapeHtml(dt)}</div>
              <div class="clin-queue-ai">${escapeHtml(item.ai_status_line)}</div>
              <div class="clin-queue-meta">Severity ${escapeHtml(item.clinical_severity_pct)} · ${escapeHtml(item.ai_label || '—')}</div>
              <div class="clin-pill-row">
                ${listMode === 'pending' && item.urgent_review ? '<span class="clin-pill clin-pill-urgent">Urgent</span>' : ''}
                ${listMode === 'pending' && (item.clinical_severity != null && item.clinical_severity >= 0.8) ? '<span class="clin-pill clin-pill-sev">High score</span>' : ''}
                <span class="clin-pill ${badgeClass(item.status_badge)}">${badgeLabel(item.status_badge)}</span>
              </div>
            </div>
          </div>
        </button>`;
    }).join('');

    mount.querySelectorAll('.clin-queue-card').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number(btn.dataset.reportId);
        if (id) selectReport(id);
      });
    });
  }

  async function loadQueue() {
    const mount = el('clin-queue-list');
    if (mount && !queue.length && listMode === 'pending') {
      mount.innerHTML = '<div class="clin-queue-loading">Loading queue…</div>';
    }
    try {
      const res  = await authFetch(`${API}/api/clinician/queue`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Queue failed');
      queue = data.queue || [];
      if (listMode === 'pending') renderList();
    } catch {
      showToast('Could not load clinician queue.', 'error');
      if (mount && listMode === 'pending') {
        mount.innerHTML = '<div class="clin-queue-empty">Queue unavailable.</div>';
      }
    }
  }

  async function loadValidated() {
    const mount = el('clin-queue-list');
    if (mount && !validatedList.length && listMode === 'validated') {
      mount.innerHTML = '<div class="clin-queue-loading">Loading validated reports…</div>';
    }
    try {
      const res  = await authFetch(`${API}/api/clinician/validated`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Validated list failed');
      validatedList = data.validated || [];
      if (listMode === 'validated') renderList();
    } catch {
      validatedList = [];
      showToast('Could not load validated reports.', 'error');
      if (mount && listMode === 'validated') {
        mount.innerHTML = '<div class="clin-queue-empty">Validated list unavailable.</div>';
      }
    }
  }

  async function switchListMode(mode) {
    if (listMode === mode) return;
    listMode = mode;
    updateTabs();
    setMasterHeader();
    setEmptyCopy();
    activeReportId = null;
    el('clin-empty-state').hidden = false;
    el('clin-workspace').hidden = true;
    el('clin-hitl-aside').hidden = true;

    if (mode === 'pending') {
      const mount = el('clin-queue-list');
      if (mount) mount.innerHTML = '<div class="clin-queue-loading">Loading queue…</div>';
      await loadQueue();
      if (queue.length) await selectReport(queue[0].report_id);
      else renderList();
    } else {
      const mount = el('clin-queue-list');
      if (mount) mount.innerHTML = '<div class="clin-queue-loading">Loading validated reports…</div>';
      await loadValidated();
      if (validatedList.length) await selectReport(validatedList[0].report_id);
      else renderList();
    }
  }

  el('clin-tab-pending')?.addEventListener('click', () => switchListMode('pending'));
  el('clin-tab-validated')?.addEventListener('click', () => switchListMode('validated'));

  function setB64Img(imgEl, b64) {
    if (!imgEl) return;
    if (b64) {
      imgEl.src = `data:image/png;base64,${b64}`;
      imgEl.removeAttribute('hidden');
    } else {
      imgEl.removeAttribute('src');
      imgEl.alt = 'Unavailable';
    }
  }

  function wrapPannableFrame(frame) {
    if (!frame || frame.querySelector('.xai-panel-inner')) return;
    const img = frame.querySelector('img');
    if (!img) return;
    const inner = document.createElement('div');
    inner.className = 'xai-panel-inner';
    frame.appendChild(inner);
    inner.appendChild(img);
  }

  function bindPannable(frame) {
    if (!frame || frame.dataset.panBound === '1') return;
    frame.dataset.panBound = '1';
    wrapPannableFrame(frame);
    const inner = frame.querySelector('.xai-panel-inner');
    if (!inner) return;

    let dragging = false;
    let sx = 0, sy = 0, ox = 0, oy = 0;

    function tx() { return parseFloat(frame.dataset.panTx || '0', 10); }
    function ty() { return parseFloat(frame.dataset.panTy || '0', 10); }
    function setT(nx, ny) {
      frame.dataset.panTx = String(nx);
      frame.dataset.panTy = String(ny);
      const sc = inner.dataset.scale || '1';
      inner.style.transform = `translate(${nx}px, ${ny}px) scale(${sc})`;
    }

    frame.addEventListener('mousedown', e => {
      if (e.button !== 0) return;
      dragging = true;
      frame.classList.add('is-dragging');
      sx = e.clientX;
      sy = e.clientY;
      ox = tx();
      oy = ty();
    });

    window.addEventListener('mousemove', e => {
      if (!dragging) return;
      setT(ox + (e.clientX - sx), oy + (e.clientY - sy));
    });

    window.addEventListener('mouseup', () => {
      if (!dragging) return;
      dragging = false;
      frame.classList.remove('is-dragging');
    });

    inner.dataset.scale = '1';
    inner.addEventListener('dblclick', () => {
      const sc = inner.dataset.scale === '1' ? '1.35' : '1';
      inner.dataset.scale = sc;
      setT(tx(), ty());
    });
  }

  function resetVerdictUi() {
    selectedVerdict = null;
    el('btn-validate-ai')?.classList.remove('is-selected');
    el('btn-override-ai')?.classList.remove('is-selected');
    const ob = el('hitl-override-block');
    if (ob) ob.hidden = true;
    const sel = el('override-category');
    if (sel) sel.value = '';
  }

  function tierSeverityClass(pctNum) {
    if (pctNum == null || Number.isNaN(pctNum)) return 'sev-unknown';
    if (pctNum >= 80) return 'sev-high';
    if (pctNum >= 50) return 'sev-mid';
    return 'sev-low';
  }

  function updatePotentialSeverityBadges(label, softmaxScore, potentialEl, severityEl) {
    if (!potentialEl || !severityEl) return;
    const isPotential = (label || '') === 'Potential';
    potentialEl.textContent = isPotential ? 'High Potential' : 'Low Potential';
    potentialEl.className = 'ai-potential-badge ' + (isPotential ? 'is-high' : 'is-low');
    const pctNum = softmaxScore != null ? softmaxScore * 100 : null;
    if (pctNum != null && !Number.isNaN(pctNum)) {
      severityEl.textContent = `${pctNum.toFixed(1)}%`;
      severityEl.className = 'ai-severity-badge ' + tierSeverityClass(pctNum);
    } else {
      severityEl.textContent = '—';
      severityEl.className = 'ai-severity-badge sev-unknown';
    }
  }

  function updateAiRecommendationCard(data) {
    const label = data.label || 'Unclassified';
    const isPotential = label === 'Potential';
    updatePotentialSeverityBadges(
      label,
      data.softmax_score,
      el('ai-potential-badge'),
      el('ai-severity-badge'),
    );
    const main = el('ai-conclusion-main');
    if (main) {
      main.textContent = isPotential
        ? 'Pattern weighted toward elevated dysgraphia risk—use the evidence panels and educator context before adjudicating.'
        : 'Pattern weighted toward lower dysgraphia risk at this screening—still review panels if clinical context suggests otherwise.';
    }
  }

  function populateReadonly(data) {
    const verdict = data.verdict;
    let vText = '—';
    if (verdict === 'verify') vText = 'Concur / validated AI';
    else if (verdict === 'disagree') vText = 'Override / requires follow-up';
    el('hitl-readonly-verdict').textContent = vText;

    const overrideCat = (data.override_category || '').trim();
    const showOv = verdict === 'disagree' && overrideCat;
    const odt = el('hitl-readonly-override-dt');
    const odd = el('hitl-readonly-override-dd');
    if (odt) odt.hidden = !showOv;
    if (odd) {
      odd.hidden = !showOv;
      if (showOv) odd.textContent = overrideCat;
    }

    const notesEl = el('hitl-readonly-notes');
    if (notesEl) {
      const n = (data.clinician_notes || '').trim();
      notesEl.textContent = n || '—';
    }

    updatePotentialSeverityBadges(
      data.label,
      data.softmax_score,
      el('hitl-readonly-potential-badge'),
      el('hitl-readonly-severity-badge'),
    );

    const dateEl = el('hitl-readonly-date');
    if (dateEl) dateEl.textContent = (data.created_at || '').split('T')[0] || '—';

    const findings = (data.findings || '').trim();
    const fw = el('hitl-readonly-findings-wrap');
    const ft = el('hitl-readonly-findings');
    if (fw && ft) {
      if (findings) {
        fw.hidden = false;
        ft.textContent = findings;
      } else {
        fw.hidden = true;
        ft.textContent = '—';
      }
    }
  }

  async function selectReport(reportId) {
    const readOnly = listMode === 'validated';
    activeReportId = reportId;
    renderList();
    resetVerdictUi();
    if (!readOnly) {
      el('clinician-diagnostic-notes').value = '';
    }
    const idLabel = `RPT-${String(reportId).padStart(4, '0')}`;
    el('hitl-active-id').textContent = idLabel;
    el('hitl-readonly-id').textContent = idLabel;

    el('clin-empty-state').hidden = true;
    el('clin-workspace').hidden = false;
    el('clin-hitl-aside').hidden = false;
    el('hitl-panel-pending').hidden = readOnly;
    el('hitl-panel-readonly').hidden = !readOnly;

    try {
      const res  = await authFetch(`${API}/api/report/${reportId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Report not found');
      if (activeReportId !== reportId) return;

      const ctx = (data.educator_context_display || data.notes || '').trim();
      const ctxBox = el('educator-context-box');
      const ctxText = el('educator-context-text');
      if (ctx) {
        ctxBox.hidden = false;
        ctxText.textContent = ctx;
      } else {
        ctxBox.hidden = false;
        ctxText.textContent = 'No educator context was provided for this upload.';
      }

      setB64Img(el('panel-1-img'), data.original_b64);
      setB64Img(el('panel-2-img'), data.otsu_binarized_b64 || data.original_b64);
      setB64Img(el('panel-3-img'), data.gradcam_b64);
      setB64Img(el('panel-4-img'), data.shap_b64);

      ['panel-1-frame', 'panel-2-frame'].forEach(fid => {
        const fr = el(fid);
        if (fr) {
          fr.dataset.panTx = '0';
          fr.dataset.panTy = '0';
        }
        const inner = fr?.querySelector('.xai-panel-inner');
        if (inner) {
          inner.dataset.scale = '1';
          inner.style.transform = 'translate(0px, 0px) scale(1)';
        }
      });

      bindPannable(el('panel-1-frame'));
      bindPannable(el('panel-2-frame'));

      updateAiRecommendationCard(data);

      const panelReadOnly = listMode === 'validated';
      const pendingEl = el('hitl-panel-pending');
      const readonlyEl = el('hitl-panel-readonly');
      if (pendingEl) pendingEl.hidden = panelReadOnly;
      if (readonlyEl) readonlyEl.hidden = !panelReadOnly;
      if (panelReadOnly) populateReadonly(data);
    } catch (err) {
      showToast(err.message || 'Could not load report.', 'error');
    }
  }

  el('btn-validate-ai').addEventListener('click', () => {
    selectedVerdict = 'verify';
    el('btn-validate-ai').classList.add('is-selected');
    el('btn-override-ai').classList.remove('is-selected');
    el('hitl-override-block').hidden = true;
  });

  el('btn-override-ai').addEventListener('click', () => {
    selectedVerdict = 'disagree';
    el('btn-override-ai').classList.add('is-selected');
    el('btn-validate-ai').classList.remove('is-selected');
    el('hitl-override-block').hidden = false;
  });

  async function downloadReportPdf(reportId) {
    try {
      const res = await authFetch(`${API}/api/report/${reportId}/pdf`);
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `inscriptio_report_RPT${String(reportId).padStart(4, '0')}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch { /* PDF optional */ }
  }

  el('btn-submit-next').addEventListener('click', async () => {
    if (!activeReportId) {
      showToast('Select a report first.', 'warning');
      return;
    }
    if (listMode !== 'pending') return;
    if (!selectedVerdict) {
      showToast('Choose validate or override.', 'warning');
      return;
    }
    const notes = el('clinician-diagnostic-notes').value.trim();
    if (notes.length < 3) {
      showToast('Diagnostic notes must be at least 3 characters.', 'warning');
      return;
    }

    let overrideCategory = null;
    if (selectedVerdict === 'disagree') {
      const sel = el('override-category');
      const opt = sel?.options?.[sel.selectedIndex];
      if (!sel || !opt?.value) {
        showToast('Select an override category.', 'warning');
        return;
      }
      overrideCategory = opt.text.replace(/^—\s*/, '').trim();
    }

    const btn = el('btn-submit-next');
    btn.disabled = true;
    try {
      const res = await authFetch(`${API}/api/clinician/report/${activeReportId}/adjudicate`, {
        method: 'POST',
        body: JSON.stringify({
          verdict: selectedVerdict,
          clinician_notes: notes,
          override_category: overrideCategory,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Save failed');

      showToast('Saved. Generating PDF for the educator…', 'success');
      await downloadReportPdf(activeReportId);

      activeReportId = null;
      resetVerdictUi();
      el('clinician-diagnostic-notes').value = '';

      await loadQueue();
      if (queue.length) {
        await selectReport(queue[0].report_id);
      } else {
        el('clin-empty-state').hidden = false;
        el('clin-workspace').hidden = true;
        el('clin-hitl-aside').hidden = true;
        setEmptyCopy();
        showToast('Queue is clear.', 'info');
      }
    } catch (e) {
      showToast(e.message || 'Submit failed.', 'error');
    } finally {
      btn.disabled = false;
    }
  });

  setEmptyCopy();
  setMasterHeader();
  updateTabs();
  await loadQueue();
  if (queue.length) await selectReport(queue[0].report_id);
});
