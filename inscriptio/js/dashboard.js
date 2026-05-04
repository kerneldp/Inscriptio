/* ============================================================
   inscriptio — dashboard.js
   Logic for 02_main_dashboard.html
   DEV NOTE: Replace all data operations with API calls:
     GET /api/stats/summary
     GET /api/students?filter=...&search=...
     GET /api/activity/recent?limit=10
   ============================================================ */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const user = Session.require();
  if (!user) return;

  // Populate sidebar user info
  populateSidebarUser();
  initSidebarNav();

  // ── Search bar ─────────────────────────────────────────────
  const searchInput = document.getElementById('student-search');
  const tableBody   = document.getElementById('student-table-body');
  const rows        = tableBody ? Array.from(tableBody.querySelectorAll('tr[data-student]')) : [];

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      rows.forEach(row => {
        const text = row.dataset.student.toLowerCase();
        row.style.display = (!q || text.includes(q)) ? '' : 'none';
      });
    });
  }

  // ── Filter pills ───────────────────────────────────────────
  const pills = document.querySelectorAll('.filter-pill');

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');

      const filter = pill.dataset.filter || 'all';
      // DEV NOTE: Replace with GET /api/students?filter=filter
      rows.forEach(row => {
        const status = row.dataset.status || 'all';
        row.style.display = (filter === 'all' || status === filter) ? '' : 'none';
      });
    });
  });

  // ── "View Report" buttons ──────────────────────────────────
  const reportBtns = document.querySelectorAll('.view-report-btn');
  reportBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // DEV NOTE: Pass student ID as query param; report page reads it
      // e.g. navigate('report?id=' + btn.dataset.student)
      navigate('report');
    });
  });

  // ── FAB quick upload ──────────────────────────────────────
  const fab = document.getElementById('fab-upload');
  if (fab) {
    fab.addEventListener('click', () => navigate('upload'));
  }

  // ── "Add Student" action ──────────────────────────────────
  const addStudentBtn = document.getElementById('add-student-btn');
  if (addStudentBtn) {
    addStudentBtn.addEventListener('click', () => {
      showToast('DEV: Add Student modal not yet wired to backend.', 'warning');
    });
  }

  // ── "View all" activity ────────────────────────────────────
  const viewAllBtn = document.getElementById('view-all-activity');
  if (viewAllBtn) {
    viewAllBtn.addEventListener('click', () => {
      showToast('DEV: Full activity log — not yet implemented.', 'info');
    });
  }
});
