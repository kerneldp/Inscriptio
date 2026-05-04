/* ============================================================
   inscriptio — upload.js
   Logic for 03_upload_processing.html
   DEV NOTE:
     POST /api/preprocess/preview  → { original_b64, binarized_b64, steps }
     POST /api/analyze             → { reportId, studentId, status }
     GET  /api/report/:reportId    → poll until status === "ready"
   ============================================================ */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const user = Session.require();
  if (!user) return;

  populateSidebarUser();
  initSidebarNav();

  // ── Element refs ──────────────────────────────────────────
  const dropzone      = document.getElementById('dropzone');
  const fileInput     = document.getElementById('file-input');
  const browseBtn     = document.getElementById('browse-btn');
  const fileClearBtn  = document.getElementById('file-clear');
  const fileInfoEl    = document.getElementById('file-info');
  const fileNameEl    = document.getElementById('file-name');
  const fileSizeEl    = document.getElementById('file-size');

  const previewOriginal   = document.getElementById('preview-original');
  const previewBinarized  = document.getElementById('preview-binarized');

  const stepIcons  = document.querySelectorAll('.step-icon');
  const stepStatus = document.querySelectorAll('.step-status');

  const analyzeBtn  = document.getElementById('analyze-btn');
  const analyzeTxt  = document.getElementById('analyze-btn-text');

  let selectedFile = null;

  // ── Step state helpers ────────────────────────────────────
  function setStep(index, state) {
    // state: 'pending' | 'active' | 'done'
    const icon   = stepIcons[index];
    const status = stepStatus[index];
    if (!icon || !status) return;

    icon.className = `step-icon ${state}`;

    if (state === 'done') {
      icon.textContent  = '✓';
      status.textContent = 'Done';
      status.className  = 'step-status done';
    } else if (state === 'active') {
      icon.textContent  = '⟳';
      status.textContent = 'Processing…';
      status.className  = 'step-status';
    } else {
      icon.textContent  = '○';
      status.textContent = 'Waiting';
      status.className  = 'step-status';
    }
  }

  function resetSteps() {
    setStep(0, 'pending');
    setStep(1, 'pending');
    setStep(2, 'pending');
    setStep(3, 'pending');
  }

  // ── File selection ────────────────────────────────────────
  function handleFile(file) {
    if (!file) return;

    const allowed = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!allowed.includes(file.type)) {
      showToast('Only PNG or JPG files are supported.', 'error');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      showToast('File must be under 10 MB.', 'error');
      return;
    }

    selectedFile = file;

    // Show file info
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = (file.size / 1024).toFixed(1) + ' KB';
    fileInfoEl.style.display = 'flex';

    dropzone.classList.add('has-file');
    dropzone.querySelector('.dz-title').textContent = 'Image selected';

    // Original preview
    const url = URL.createObjectURL(file);
    previewOriginal.innerHTML = `<img class="preview-img" src="${url}" alt="Original handwriting">`;

    // Simulate preprocessing steps
    // DEV NOTE: Replace with POST /api/preprocess/preview multipart request
    resetSteps();
    setStep(0, 'done'); // Uploaded

    setTimeout(() => setStep(1, 'active'), 400);
    setTimeout(() => {
      setStep(1, 'done');
      setStep(2, 'active');

      // Simulate binarized preview with a canvas filter
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = 224; canvas.height = 224;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, 224, 224);
        const imageData = ctx.getImageData(0, 0, 224, 224);
        const data = imageData.data;

        // Simple grayscale + threshold (Otsu-like mockup)
        for (let i = 0; i < data.length; i += 4) {
          const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
          const val  = gray < 128 ? 0 : 255;
          data[i] = data[i+1] = data[i+2] = val;
        }
        ctx.putImageData(imageData, 0, 0);

        previewBinarized.innerHTML =
          `<img class="preview-img" src="${canvas.toDataURL()}" alt="Binarized 224×224">`;
      };
      img.src = url;
    }, 1200);

    setTimeout(() => {
      setStep(2, 'done');
      setStep(3, 'active');
    }, 2200);

    setTimeout(() => {
      setStep(3, 'done');
      analyzeBtn.disabled = false;
    }, 3000);

    analyzeBtn.disabled = true; // re-disable until steps complete
  }

  // ── Drag and drop ─────────────────────────────────────────
  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    handleFile(file);
  });

  // ── Browse button ─────────────────────────────────────────
  browseBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  // ── Clear file ────────────────────────────────────────────
  if (fileClearBtn) {
    fileClearBtn.addEventListener('click', () => {
      selectedFile = null;
      fileInput.value = '';
      fileInfoEl.style.display = 'none';
      dropzone.classList.remove('has-file');
      dropzone.querySelector('.dz-title').textContent = 'Drop the handwriting image here';
      previewOriginal.innerHTML = `
        <div class="preview-placeholder">
          <span style="font-size:1.8rem">🖊️</span>
          <div class="preview-placeholder-text">Original image appears here after upload</div>
        </div>`;
      previewBinarized.innerHTML = `
        <div class="preview-placeholder">
          <span style="font-size:1.8rem">⬛</span>
          <div class="preview-placeholder-text">Otsu-binarized 224×224 tensor appears here</div>
        </div>`;
      resetSteps();
      analyzeBtn.disabled = true;
    });
  }

  // ── Analyze button ────────────────────────────────────────
  analyzeBtn.disabled = true; // disabled until file ready

  analyzeBtn.addEventListener('click', () => {
    if (!selectedFile) {
      showToast('Please upload a handwriting image first.', 'warning');
      return;
    }

    const student = document.getElementById('student-select').value;
    if (!student) {
      showToast('Please select a student before analyzing.', 'warning');
      return;
    }

    // DEV NOTE: Replace with POST /api/analyze multipart/form-data
    // { studentId, sessionDate, classId, imageFile }
    analyzeBtn.disabled = true;
    analyzeTxt.textContent = 'Analyzing…';

    showToast('Running HXAI pipeline — this may take a few seconds.', 'info');

    // Simulate processing delay then navigate to report
    setTimeout(() => {
      showToast('Analysis complete! Redirecting to report…', 'success');
      setTimeout(() => navigate('report'), 800);
    }, 2500);
  });
});
