/* ============================================================
   inscriptio — dashboard.js
   Logic for 02_main_dashboard.html
   GET /api/stats/summary
   GET /api/students?search=
   GET /api/activity/recent
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', async () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  // ── Summary cards ─────────────────────────────────────────
  async function loadSummary() {
    try {
      const res  = await authFetch(`${API}/api/stats/summary`);
      const data = await res.json();
      document.querySelectorAll('.stat-card').forEach(card => {
        const eyebrow = card.querySelector('.stat-eyebrow');
        const value   = card.querySelector('.stat-value');
        if (!eyebrow || !value) return;
        const label = eyebrow.textContent.trim().toLowerCase();
        if (label.includes('total'))   value.textContent = data.total_screenings ?? 0;
        if (label.includes('pending')) value.textContent = data.pending_reviews  ?? 0;
        if (label.includes('flagged')) value.textContent = data.flagged_cases    ?? 0;
        if (label.includes('active'))  value.textContent = data.active_students  ?? 0;
      });
    } catch { showToast('Could not load summary. Is the backend running?', 'error'); }
  }

  // ── Student table ─────────────────────────────────────────
  async function loadStudents(search = '') {
    try {
      const res  = await authFetch(`${API}/api/students?search=${encodeURIComponent(search)}`);
      const data = await res.json();
      const body = document.getElementById('student-table-body');
      if (!body) return;

      if (!data.students?.length) {
        body.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--ghost);">No students found.</td></tr>`;
        return;
      }

      body.innerHTML = data.students.map(s => {
        const initials    = s.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        const label       = s.latest_label || '—';
        const score       = s.latest_score != null ? (s.latest_score * 100).toFixed(1) + '%' : '—';
        const date        = s.latest_date  ? s.latest_date.split('T')[0] : '—';
        const statusClass = label === 'Potential' ? 'potential' : label === 'Low Potential' ? 'low' : 'pending';
        const disabled = !s.latest_report_id;
        const btn = disabled
          ? `<button class="action-btn view-report-btn" disabled style="opacity:0.5;cursor:not-allowed;">No Report</button>`
          : `<button class="action-btn view-report-btn" onclick="sessionStorage.setItem('current_report_id','${s.latest_report_id}'); navigate('report')">View Report</button>`;
        return `
        <tr data-student="${s.name}" data-status="${statusClass}">
          <td>
            <div class="student-cell">
              <div class="stu-avatar">${initials}</div>
              <div>
                <div class="stu-name">${s.name}</div>
                <div class="stu-id">#STU-${String(s.id).padStart(3,'0')}</div>
              </div>
            </div>
          </td>
          <td class="td-mono">${s.class || '—'}</td>
          <td class="td-mono">${date}</td>
          <td class="td-score">${score}</td>
          <td><span class="status-pill ${statusClass}"><span class="status-dot"></span>${label}</span></td>
          <td>${btn}</td>
        </tr>`;
      }).join('');

    } catch { showToast('Could not load students.', 'error'); }
  }

  // ── Recent activity ───────────────────────────────────────
  async function loadRecentActivity() {
    try {
      const res  = await authFetch(`${API}/api/activity/recent`);
      const data = await res.json();
      const list = document.querySelector('.activity-list');
      if (!list) return;

      if (!data.recent?.length) {
        list.innerHTML = `<div style="text-align:center;padding:24px;color:var(--ghost);">No recent activity yet.</div>`;
        return;
      }

      list.innerHTML = data.recent.map(r => {
        const dotClass = r.label === 'Potential' ? 'act-dot-danger' : 'act-dot-teal';
        const score    = r.softmax_score ? (r.softmax_score * 100).toFixed(1) + '%' : '';
        const date     = r.created_at ? r.created_at.split('T')[0] : '';
        return `
        <div class="activity-item">
          <div class="activity-dot ${dotClass}"></div>
          <div class="activity-body">
            <div class="activity-desc">
              <strong>STU-${String(r.student_id).padStart(3,'0')}</strong> screened —
              <strong>${r.label || 'Unclassified'}</strong>
              ${score ? '— confidence ' + score : ''}
            </div>
            <div class="activity-time">${date}</div>
          </div>
        </div>`;
      }).join('');

    } catch { showToast('Could not load recent activity.', 'error'); }
  }

  // ── Search ────────────────────────────────────────────────
  const searchInput = document.getElementById('student-search');
  if (searchInput) {
    let t = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(() => loadStudents(searchInput.value.trim()), 400);
    });
  }

  // ── Filter pills ──────────────────────────────────────────
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const filter = pill.dataset.filter || 'all';
      document.querySelectorAll('#student-table-body tr[data-student]').forEach(row => {
        row.style.display = (filter === 'all' || row.dataset.status === filter) ? '' : 'none';
      });
    });
  });

  // ── FAB ───────────────────────────────────────────────────
  document.getElementById('fab-upload')?.addEventListener('click', () => navigate('upload'));
  document.getElementById('add-student-btn')?.addEventListener('click',
    () => showToast('Add Student — not yet implemented.', 'warning'));
  document.getElementById('view-all-activity')?.addEventListener('click',
    () => showToast('Full activity log — not yet implemented.', 'info'));

  await Promise.all([loadSummary(), loadStudents(), loadRecentActivity()]);
});