/* ============================================================
   inscriptio — report.js
   Logic for 04_hxai_report_view.html
   DEV NOTE:
     GET  /api/report/:reportId   → full 4-panel data
     POST /api/report/:reportId/validate  → { decision: "verify"|"disagree" }
     PATCH /api/report/:reportId/notes   → { educatorNote }
     POST /api/report/:reportId/save     → commit to student history
   ============================================================ */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const user = Session.require();
  if (!user) return;

  populateSidebarUser();
  initSidebarNav();

  // ── Role-based UI ─────────────────────────────────────────
  // DEV NOTE: Replace with role check from JWT. Currently reads from session.
  const isClinicianRole = user.role === 'clinician';

  const validationRow   = document.getElementById('validation-row');
  const clinicianLocked = document.getElementById('clinician-locked');

  if (validationRow && clinicianLocked) {
    if (isClinicianRole) {
      validationRow.style.display   = 'flex';
      clinicianLocked.style.display = 'none';
    } else {
      validationRow.style.display   = 'none';
      clinicianLocked.style.display = 'block';
    }
  }

  // ── Clinician validation toggle ───────────────────────────
  let validationDecision = null;

  const verifyBtn   = document.getElementById('val-verify');
  const disagreeBtn = document.getElementById('val-disagree');

  function setValidation(decision) {
    validationDecision = decision;
    if (verifyBtn)   verifyBtn.classList.toggle('selected', decision === 'verify');
    if (disagreeBtn) disagreeBtn.classList.toggle('selected', decision === 'disagree');

    // DEV NOTE: POST /api/report/:reportId/validate { decision, clinicianId }
    showToast(
      decision === 'verify'
        ? 'Marked as Verified — save to commit.'
        : 'Marked as Disagreed — save to commit.',
      'info'
    );
  }

  if (verifyBtn)   verifyBtn.addEventListener('click',   () => setValidation('verify'));
  if (disagreeBtn) disagreeBtn.addEventListener('click', () => setValidation('disagree'));

  // ── Notes autosave simulation ─────────────────────────────
  const notesField = document.getElementById('educator-notes');
  let notesTimer   = null;

  if (notesField) {
    notesField.addEventListener('input', () => {
      clearTimeout(notesTimer);
      notesTimer = setTimeout(() => {
        // DEV NOTE: PATCH /api/report/:reportId { educatorNote: notesField.value }
        showToast('Note auto-saved.', 'info');
      }, 2000);
    });
  }

  // ── Save to history ───────────────────────────────────────
  const saveBtn = document.getElementById('save-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      if (isClinicianRole && !validationDecision) {
        showToast('Please select Verify or Disagree before saving.', 'warning');
        return;
      }
      // DEV NOTE: POST /api/report/:reportId/save { validationDecision, educatorNote }
      showToast('Report saved to student history.', 'success');
      setTimeout(() => navigate('dashboard'), 1000);
    });
  }

  // ── Discard ───────────────────────────────────────────────
  const discardBtn = document.getElementById('discard-btn');
  if (discardBtn) {
    discardBtn.addEventListener('click', () => {
      confirmModal(
        'This report and all notes will be discarded and will not be saved to the student\'s record. The action cannot be undone.',
        () => {
          // DEV NOTE: No write — abandon session / soft-delete if needed
          showToast('Report discarded.', 'warning');
          setTimeout(() => navigate('dashboard'), 800);
        }
      );
    });
  }

  // ── Confidence bar animation ──────────────────────────────
  const confBar = document.getElementById('conf-bar-fill');
  if (confBar) {
    const target = confBar.dataset.value || '87';
    // Animate from 0 to target
    confBar.style.width = '0%';
    setTimeout(() => {
      confBar.style.width = target + '%';
    }, 400);
  }
});
