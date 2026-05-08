/* ============================================================
   inscriptio — upload.js
   Logic for 03_upload_processing.html
   POST /api/report/preprocess/preview
   POST /api/report/analyze
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  // ── Element refs ──────────────────────────────────────────
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

  let selectedFile = null;

  // ── Populate student dropdown ─────────────────────────────
  async function loadStudentOptions() {
    try {
      const res  = await authFetch(`${API}/api/students`);
      const data = await res.json();
      const sel  = document.getElementById('student-select');
      if (!sel) return;
      sel.innerHTML = '<option value="">— Select student —</option>';
      (data.students || []).forEach(s => {
        const opt       = document.createElement('option');
        opt.value       = s.id;
        opt.textContent = `${s.name}${s.class ? ' (' + s.class + ')' : ''}`;
        sel.appendChild(opt);
      });
    } catch { showToast('Could not load student list.', 'error'); }
  }

  // ── Step helpers ──────────────────────────────────────────
  function setStep(i, state) {
    const icon   = stepIcons[i];
    const status = stepStatuses[i];
    if (!icon || !status) return;
    icon.className = `step-icon ${state}`;
    if (state === 'done')   { icon.textContent = '✓'; status.textContent = 'Done';        status.className = 'step-status done'; }
    else if (state === 'active') { icon.textContent = '⟳'; status.textContent = 'Processing…'; status.className = 'step-status'; }
    else                    { icon.textContent = '○'; status.textContent = 'Waiting';     status.className = 'step-status'; }
  }

  function resetSteps() { [0,1,2,3].forEach(i => setStep(i, 'pending')); }

  // ── File selection ────────────────────────────────────────
  async function handleFile(file) {
    if (!file) return;
    if (!['image/png','image/jpeg','image/jpg'].includes(file.type)) {
      showToast('Only PNG or JPG files are supported.', 'error'); return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('File must be under 10 MB.', 'error'); return;
    }

    selectedFile = file;
    fileNameEl.textContent   = file.name;
    fileSizeEl.textContent   = (file.size / 1024).toFixed(1) + ' KB';
    fileInfoEl.style.display = 'flex';
    dropzone.classList.add('has-file');
    dropzone.querySelector('.dz-title').textContent = 'Image selected';

    // Show original preview immediately
    const url = URL.createObjectURL(file);
    previewOrig.innerHTML = `<img class="preview-img" src="${url}" alt="Original">`;

    resetSteps();
    setStep(0, 'done');   // Uploaded
    setStep(1, 'active'); // Preprocessing

    analyzeBtn.disabled = true;

    // Call backend for real Otsu binarization preview
    try {
      const form = new FormData();
      form.append('file', file);
      const res  = await authFetchForm(`${API}/api/report/preprocess/preview`, form);
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Preview failed');

      setStep(1, 'done');
      setStep(2, 'active');

      // Show real binarized image from backend
      previewBin.innerHTML =
        `<img class="preview-img" src="data:image/png;base64,${data.binarized_b64}" alt="Binarized 224×224">`;

      setStep(2, 'done');
      setStep(3, 'active');

      setTimeout(() => {
        setStep(3, 'done');
        analyzeBtn.disabled = false;
      }, 400);

    } catch (err) {
      showToast(`Preprocessing failed: ${err.message}`, 'error');
      resetSteps();
    }
  }

  // ── Drag and drop ─────────────────────────────────────────
  dropzone.addEventListener('dragover',  e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', ()=> dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault(); dropzone.classList.remove('drag-over');
    handleFile(e.dataTransfer.files[0]);
  });

  browseBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

  // ── Clear ─────────────────────────────────────────────────
  fileClearBtn?.addEventListener('click', () => {
    selectedFile = null; fileInput.value = '';
    fileInfoEl.style.display = 'none';
    dropzone.classList.remove('has-file');
    dropzone.querySelector('.dz-title').textContent = 'Drop the handwriting image here';
    previewOrig.innerHTML = `<div class="preview-placeholder"><span style="font-size:1.8rem">🖊️</span><div class="preview-placeholder-text">Original image appears here after upload</div></div>`;
    previewBin.innerHTML  = `<div class="preview-placeholder"><span style="font-size:1.8rem">⬛</span><div class="preview-placeholder-text">Otsu-binarized 224×224 tensor appears here</div></div>`;
    resetSteps();
    analyzeBtn.disabled = true;
  });

  // ── Analyze ───────────────────────────────────────────────
  analyzeBtn.disabled = true;

  analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) { showToast('Please upload an image first.', 'warning'); return; }

    const sel = document.getElementById('student-select');
    if (!sel?.value) { showToast('Please select a student before analyzing.', 'warning'); return; }

    analyzeBtn.disabled    = true;
    analyzeTxt.textContent = 'Analyzing…';
    showToast('Running HXAI pipeline — this may take 30–60 seconds.', 'info');

    try {
      const form = new FormData();
      form.append('file',       selectedFile);
      form.append('student_id', sel.value);
      form.append('session_date', new Date().toISOString().split('T')[0]);

      const res  = await authFetchForm(`${API}/api/report/analyze`, form);
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Analysis failed');

      // Store report id so report.js can load it
      sessionStorage.setItem('current_report_id', data.report_id);

      showToast('Analysis complete! Redirecting to report…', 'success');
      setTimeout(() => navigate('report'), 800);

    } catch (err) {
      showToast(`Analysis failed: ${err.message}`, 'error');
      analyzeBtn.disabled    = false;
      analyzeTxt.textContent = 'Run Analysis';
    }
  });

  // ── Init ──────────────────────────────────────────────────
  loadStudentOptions();
});