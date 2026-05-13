/* ============================================================
   inscriptio — upload.js
   Logic for 03_upload_processing.html
   POST /api/report/preprocess/preview
   POST /api/report/analyze
   GET  /api/report/model/info
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

const PREVIEW_STEP_IDS = ['uploaded', 'otsu', 'resize', 'ready'];

document.addEventListener('DOMContentLoaded', () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  const dropzone     = document.getElementById('dropzone');
  const fileInput    = document.getElementById('file-input');
  const browseBtn    = document.getElementById('browse-btn');
  const fileClearBtn = document.getElementById('file-clear');
  const fileInfoEl   = document.getElementById('file-info');
  const fileNameEl   = document.getElementById('file-name');
  const fileSizeEl   = document.getElementById('file-size');
  const previewOrig  = document.getElementById('preview-original');
  const previewBin   = document.getElementById('preview-binarized');
  const stepIcons    = document.querySelectorAll('.step-icon');
  const stepStatuses = document.querySelectorAll('.step-status');
  const analyzeBtn   = document.getElementById('analyze-btn');
  const analyzeTxt   = document.getElementById('analyze-btn-text');
  const studentSelect = document.getElementById('student-select');
  const classDisplay  = document.getElementById('student-class-display');
  const sessionDateEl = document.getElementById('session-date');

  let selectedFile     = null;
  let previewObjectUrl = null;
  let studentsCache    = [];

  const PLACEHOLDER_ORIG = `<div class="preview-placeholder"><span style="font-size:1.8rem">🖊️</span><div class="preview-placeholder-text">Original image appears<br>here after upload</div></div>`;
  const PLACEHOLDER_BIN  = `<div class="preview-placeholder"><span style="font-size:1.8rem">⬛</span><div class="preview-placeholder-text">Otsu-binarized 224×224<br>preview appears here</div></div>`;

  if (sessionDateEl && !sessionDateEl.value) {
    sessionDateEl.value = new Date().toISOString().split('T')[0];
  }

  function setStep(i, state) {
    const icon   = stepIcons[i];
    const status = stepStatuses[i];
    if (!icon || !status) return;
    icon.className = `step-icon ${state}`;
    if (state === 'done') {
      icon.textContent = '✓';
      status.textContent = 'Done';
      status.className = 'step-status done';
    } else if (state === 'active') {
      icon.textContent = '⟳';
      status.textContent = 'Processing…';
      status.className = 'step-status';
    } else {
      icon.textContent = '○';
      status.textContent = 'Waiting';
      status.className = 'step-status';
    }
  }

  function resetSteps() {
    [0, 1, 2, 3].forEach((i) => setStep(i, 'pending'));
  }

  function applyStepsFromResponse(steps) {
    if (!steps || !Array.isArray(steps)) return;
    const byId = Object.fromEntries(steps.map((s) => [s.id, s.status]));
    PREVIEW_STEP_IDS.forEach((id, i) => {
      const st = byId[id];
      if (st === 'done') setStep(i, 'done');
      else if (st === 'active') setStep(i, 'active');
      else if (st === 'error') setStep(i, 'pending');
      else setStep(i, 'pending');
    });
  }

  function finishPreviewStepsFallback() {
    [0, 1, 2, 3].forEach((i) => setStep(i, 'done'));
  }

  async function loadStudentOptions() {
    try {
      const res  = await authFetch(`${API}/api/students`);
      const data = await res.json();
      const sel    = document.getElementById('student-select');
      if (!sel) return;
      studentsCache = data.students || [];
      sel.innerHTML = '<option value="">— Choose a student —</option>';
      studentsCache.forEach((s) => {
        const opt       = document.createElement('option');
        opt.value       = String(s.id);
        opt.textContent = `${s.name}${s.class ? ' (' + s.class + ')' : ''}`;
        sel.appendChild(opt);
      });
    } catch {
      showToast('Could not load student list.', 'error');
    }
  }

  function syncClassFromStudent() {
    if (!studentSelect || !classDisplay) return;
    const id = parseInt(studentSelect.value, 10);
    const s  = studentsCache.find((x) => x.id === id);
    classDisplay.value = s && s.class ? s.class : '';
  }

  studentSelect?.addEventListener('change', syncClassFromStudent);

  async function loadModelInfo() {
    const ids = {
      name:    'model-info-name',
      xai:     'model-info-xai',
      input:   'model-info-input',
      pre:     'model-info-pre',
      output:  'model-info-output',
      version: 'model-info-version',
    };
    const set = (key, text) => {
      const el = document.getElementById(ids[key]);
      if (el) el.textContent = text;
    };
    try {
      const res  = await authFetch(`${API}/api/report/model/info`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      set('name', data.model_name || '—');
      set('xai', data.explainability || '—');
      set('input', data.input_size || '—');
      set('pre', data.preprocessing || '—');
      set('output', data.output || '—');
      set('version', data.model_version_hash || '—');
    } catch {
      ['name', 'xai', 'input', 'pre', 'output', 'version'].forEach((k) => set(k, '—'));
    }
  }

  async function handleFile(file) {
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/jpg'].includes(file.type)) {
      showToast('Only PNG or JPG files are supported.', 'error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('File must be under 10 MB.', 'error');
      return;
    }

    if (previewObjectUrl) {
      URL.revokeObjectURL(previewObjectUrl);
      previewObjectUrl = null;
    }

    selectedFile = file;
    fileNameEl.textContent   = file.name;
    fileSizeEl.textContent   = (file.size / 1024).toFixed(1) + ' KB';
    fileInfoEl.style.display = 'flex';
    dropzone.classList.add('has-file');
    dropzone.querySelector('.dz-title').textContent = 'Image selected';

    previewObjectUrl = URL.createObjectURL(file);
    previewOrig.innerHTML = `<img class="preview-img" src="${previewObjectUrl}" alt="Original">`;

    resetSteps();
    setStep(0, 'done');
    setStep(1, 'active');

    analyzeBtn.disabled = true;

    try {
      const form = new FormData();
      form.append('file', file);
      const res  = await authFetchForm(`${API}/api/report/preprocess/preview`, form);
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Preview failed');

      if (data.steps && data.steps.length) {
        applyStepsFromResponse(data.steps);
      } else {
        finishPreviewStepsFallback();
      }

      const binB64 = data.thumbnail_b64 || data.binarized_b64;
      previewBin.innerHTML =
        `<img class="preview-img" src="data:image/png;base64,${binB64}" alt="Binarized 224×224">`;

      analyzeBtn.disabled = false;
    } catch (err) {
      showToast(`Preprocessing failed: ${err.message}`, 'error');
      resetSteps();
      previewBin.innerHTML = PLACEHOLDER_BIN;
    }
  }

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    handleFile(e.dataTransfer.files[0]);
  });

  browseBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  fileClearBtn?.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    fileInfoEl.style.display = 'none';
    dropzone.classList.remove('has-file');
    dropzone.querySelector('.dz-title').textContent = 'Drop the handwriting image here';
    if (previewObjectUrl) {
      URL.revokeObjectURL(previewObjectUrl);
      previewObjectUrl = null;
    }
    previewOrig.innerHTML = PLACEHOLDER_ORIG;
    previewBin.innerHTML  = PLACEHOLDER_BIN;
    resetSteps();
    analyzeBtn.disabled = true;
  });

  analyzeBtn.disabled = true;

  analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) {
      showToast('Please upload an image first.', 'warning');
      return;
    }

    if (!studentSelect?.value) {
      showToast('Please select a student before analyzing.', 'warning');
      return;
    }

    const sessionDate =
      sessionDateEl?.value || new Date().toISOString().split('T')[0];

    analyzeBtn.disabled    = true;
    analyzeTxt.textContent = 'Analyzing…';
    showToast('Running analysis on the server — this may take up to a minute.', 'info');

    try {
      const form = new FormData();
      form.append('file', selectedFile);
      form.append('student_id', studentSelect.value);
      form.append('session_date', sessionDate);
      const ctx = document.getElementById('upload-educator-context')?.value?.trim() || '';
      if (ctx) form.append('educator_context', ctx);
      const urgent = document.getElementById('upload-urgent')?.checked;
      form.append('urgent_review', urgent ? 'true' : 'false');

      const res  = await authFetchForm(`${API}/api/report/analyze`, form);
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Analysis failed');

      sessionStorage.setItem('current_report_id', data.report_id);

      showToast('Analysis complete. Opening report…', 'success');
      setTimeout(() => navigate('report'), 800);
    } catch (err) {
      showToast(`Analysis failed: ${err.message}`, 'error');
      analyzeBtn.disabled    = false;
      analyzeTxt.textContent = 'Run XAI Analysis';
    }
  });

  loadStudentOptions();
  loadModelInfo();
});
