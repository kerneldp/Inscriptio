/* ============================================================
   inscriptio — dashboard.js
   Logic for 02_main_dashboard.html
   GET /api/stats/summary
   GET /api/students?search=
   GET /api/activity/recent?week_only=&limit=
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';
const STUDENTS_PER_PAGE = 10;

document.addEventListener('DOMContentLoaded', async () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  let studentCache = [];
  let studentPage = 1;

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Summary cards ─────────────────────────────────────────
  function setStatChip(card, text, tone) {
    const chip = card.querySelector('.stat-chip');
    if (!chip || chip.classList.contains('warn')) return;
    chip.textContent = text;
    chip.className = 'stat-chip ' + (tone || 'neutral');
  }

  async function loadSummary() {
    try {
      const res  = await authFetch(`${API}/api/stats/summary`);
      const data = await res.json();
      const weekN = Number(data.screenings_this_week) || 0;
      const todayFlagged = Number(data.flagged_potential_today) || 0;
      const newStudentsWeek = Number(data.students_new_this_week) || 0;

      document.querySelectorAll('.stat-card').forEach(card => {
        const eyebrow = card.querySelector('.stat-eyebrow');
        const value   = card.querySelector('.stat-value');
        if (!eyebrow || !value) return;
        const label = eyebrow.textContent.trim().toLowerCase();
        if (label.includes('total')) {
          value.textContent = data.total_screenings ?? 0;
          if (weekN > 0) {
            setStatChip(card, `↑ +${weekN} this week`, 'up');
          } else {
            setStatChip(card, 'No new this week', 'neutral');
          }
        } else if (label.includes('pending')) {
          value.textContent = data.pending_reviews ?? 0;
        } else if (label.includes('flagged')) {
          value.textContent = data.flagged_cases ?? 0;
          if (todayFlagged > 0) {
            setStatChip(card, `↑ ${todayFlagged} new today`, 'alert');
          } else {
            setStatChip(card, 'No new today', 'neutral');
          }
        } else if (label.includes('active')) {
          value.textContent = data.active_students ?? 0;
          if (newStudentsWeek > 0) {
            setStatChip(card, `↑ ${newStudentsWeek} new this week`, 'up');
          } else {
            setStatChip(card, 'Stable', 'neutral');
          }
        }
      });
    } catch { showToast('Could not load summary. Is the backend running?', 'error'); }
  }

  // ── Student directory: filter state + pagination ───────────
  function statusClassForStudent(s) {
    const label = s.latest_label || '';
    if (label === 'Potential') return 'potential';
    if (label === 'Low Potential') return 'low';
    return 'pending';
  }

  function getFilterState() {
    const pill = document.querySelector('#student-filter-bar .filter-pill.active');
    if (!pill) return { kind: 'all' };
    if (pill.dataset.filterType === 'class') {
      return { kind: 'class', value: (pill.dataset.classValue || '').trim() };
    }
    if (pill.dataset.filter === 'all') return { kind: 'all' };
    return { kind: 'status', filter: pill.dataset.filter || 'all' };
  }

  function applyFilterState(state) {
    const pills = document.querySelectorAll('#student-filter-bar .filter-pill');
    let found = false;
    pills.forEach(p => {
      let active = false;
      if (state.kind === 'all') {
        active = p.dataset.filter === 'all';
      } else if (state.kind === 'status') {
        active = p.dataset.filterType === 'status' && p.dataset.filter === state.filter;
      } else if (state.kind === 'class') {
        active = p.dataset.filterType === 'class' && (p.dataset.classValue || '').trim() === state.value;
      }
      if (active) found = true;
      p.classList.toggle('active', active);
    });
    if (!found) {
      pills.forEach(p => p.classList.toggle('active', p.dataset.filter === 'all'));
    }
  }

  function studentMatchesFilter(s, state) {
    if (state.kind === 'all') return true;
    if (state.kind === 'class') {
      return (s.class || '').trim() === state.value;
    }
    return statusClassForStudent(s) === state.filter;
  }

  function rebuildClassPills(students) {
    const mount = document.getElementById('class-filter-mount');
    if (!mount) return;
    const state = getFilterState();
    mount.innerHTML = '';
    const classes = [...new Set(students.map(s => (s.class || '').trim()).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b));
    for (const c of classes) {
      const pill = document.createElement('div');
      pill.className = 'filter-pill';
      pill.dataset.filterType = 'class';
      pill.dataset.classValue = c;
      pill.textContent = c;
      mount.appendChild(pill);
    }
    if (state.kind === 'class' && !classes.includes(state.value)) {
      applyFilterState({ kind: 'all' });
    } else {
      applyFilterState(state);
    }
  }

  function studentRowHtml(s) {
    const initials = s.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    const label    = s.latest_label || '—';
    const score    = s.latest_score != null ? (s.latest_score * 100).toFixed(1) + '%' : '—';
    const date     = s.latest_date ? s.latest_date.split('T')[0] : '—';
    const statusClass = statusClassForStudent(s);
    const disabled = !s.latest_report_id;
    const safeName = escapeHtml(s.name);
    const btn = disabled
      ? '<button class="action-btn view-report-btn" disabled style="opacity:0.5;cursor:not-allowed;">No Report</button>'
      : `<button class="action-btn view-report-btn" onclick="sessionStorage.setItem('current_report_id','${s.latest_report_id}'); navigate('report')">View Report</button>`;
    return `
        <tr data-student="${escapeHtml(s.name)}" data-status="${statusClass}">
          <td>
            <div class="student-cell">
              <div class="stu-avatar">${escapeHtml(initials)}</div>
              <div>
                <div class="stu-name">${safeName}</div>
                <div class="stu-id">#STU-${String(s.id).padStart(3, '0')}</div>
              </div>
            </div>
          </td>
          <td class="td-mono">${escapeHtml(s.class || '—')}</td>
          <td class="td-mono">${escapeHtml(date)}</td>
          <td class="td-score">${escapeHtml(score)}</td>
          <td><span class="status-pill ${statusClass}"><span class="status-dot"></span>${escapeHtml(label)}</span></td>
          <td>${btn}</td>
        </tr>`;
  }

  function renderPagination(totalPages, totalRows) {
    const nav = document.getElementById('student-pagination');
    if (!nav) return;
    if (totalRows === 0 || totalPages <= 1) {
      nav.hidden = true;
      nav.innerHTML = '';
      return;
    }
    nav.hidden = false;
    nav.innerHTML = `
      <button type="button" class="page-btn" data-stu-page="prev" ${studentPage <= 1 ? 'disabled' : ''}>Previous</button>
      <span class="page-indicator">Page ${studentPage} of ${totalPages} · ${totalRows} students</span>
      <button type="button" class="page-btn" data-stu-page="next" ${studentPage >= totalPages ? 'disabled' : ''}>Next</button>`;
  }

  function renderStudentDirectory() {
    const state = getFilterState();
    const filtered = studentCache.filter(s => studentMatchesFilter(s, state));
    const totalPages = Math.max(1, Math.ceil(filtered.length / STUDENTS_PER_PAGE) || 1);
    if (studentPage > totalPages) studentPage = totalPages;
    if (studentPage < 1) studentPage = 1;
    const start = (studentPage - 1) * STUDENTS_PER_PAGE;
    const pageSlice = filtered.slice(start, start + STUDENTS_PER_PAGE);
    const body = document.getElementById('student-table-body');
    if (!body) return;

    if (!filtered.length) {
      body.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--ghost);">No students match this filter.</td></tr>';
      renderPagination(1, 0);
      return;
    }

    body.innerHTML = pageSlice.map(studentRowHtml).join('');
    renderPagination(totalPages, filtered.length);
  }

  document.getElementById('student-pagination')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-stu-page]');
    if (!btn || btn.disabled) return;
    const dir = btn.getAttribute('data-stu-page');
    const state = getFilterState();
    const filtered = studentCache.filter(s => studentMatchesFilter(s, state));
    const totalPages = Math.max(1, Math.ceil(filtered.length / STUDENTS_PER_PAGE));
    if (dir === 'prev' && studentPage > 1) {
      studentPage--;
      renderStudentDirectory();
    } else if (dir === 'next' && studentPage < totalPages) {
      studentPage++;
      renderStudentDirectory();
    }
  });

  document.getElementById('student-filter-bar')?.addEventListener('click', e => {
    const pill = e.target.closest('.filter-pill');
    if (!pill) return;
    document.querySelectorAll('#student-filter-bar .filter-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    studentPage = 1;
    renderStudentDirectory();
  });

  async function loadStudents(search = '') {
    try {
      const res  = await authFetch(`${API}/api/students?search=${encodeURIComponent(search)}`);
      const data = await res.json();
      studentCache = data.students || [];
      studentPage = 1;
      rebuildClassPills(studentCache);

      if (!studentCache.length) {
        const body = document.getElementById('student-table-body');
        if (body) {
          body.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--ghost);">No students found.</td></tr>';
        }
        const nav = document.getElementById('student-pagination');
        if (nav) { nav.hidden = true; nav.innerHTML = ''; }
        return;
      }

      renderStudentDirectory();
    } catch {
      showToast('Could not load students.', 'error');
      studentCache = [];
    }
  }

  // ── Recent activity ───────────────────────────────────────
  function activityItemHtml(r) {
    const dotClass = r.label === 'Potential' ? 'act-dot-danger' : 'act-dot-teal';
    const score    = r.softmax_score ? (r.softmax_score * 100).toFixed(1) + '%' : '';
    const date     = r.created_at ? r.created_at.split('T')[0] : '';
    return `
        <div class="activity-item">
          <div class="activity-dot ${dotClass}"></div>
          <div class="activity-body">
            <div class="activity-desc">
              <strong>STU-${String(r.student_id).padStart(3, '0')}</strong> screened —
              <strong>${escapeHtml(r.label || 'Unclassified')}</strong>
              ${score ? '— confidence ' + escapeHtml(score) : ''}
            </div>
            <div class="activity-time">${escapeHtml(date)}</div>
          </div>
        </div>`;
  }

  async function loadRecentActivity() {
    const list = document.getElementById('dashboard-activity-list');
    if (!list) return;
    try {
      const res  = await authFetch(`${API}/api/activity/recent?week_only=true&limit=10`);
      const data = await res.json();

      if (!data.recent?.length) {
        list.innerHTML = '<div style="text-align:center;padding:24px;color:var(--ghost);">No activity this week yet.</div>';
        return;
      }

      list.innerHTML = data.recent.map(activityItemHtml).join('');
    } catch { showToast('Could not load recent activity.', 'error'); }
  }

  const activityModal = document.getElementById('activity-modal');

  function closeActivityModal() {
    if (!activityModal) return;
    activityModal.classList.remove('is-open');
    activityModal.setAttribute('aria-hidden', 'true');
    document.removeEventListener('keydown', onActivityModalKeydown);
  }

  function onActivityModalKeydown(e) {
    if (e.key === 'Escape') closeActivityModal();
  }

  async function openActivityModal() {
    if (!activityModal) return;
    const modalList = document.getElementById('activity-modal-list');
    if (!modalList) return;
    activityModal.classList.add('is-open');
    activityModal.setAttribute('aria-hidden', 'false');
    document.addEventListener('keydown', onActivityModalKeydown);
    modalList.innerHTML = '<div class="activity-modal-loading">Loading…</div>';
    try {
      const res  = await authFetch(`${API}/api/activity/recent?week_only=false&limit=500`);
      const data = await res.json();
      if (!data.recent?.length) {
        modalList.innerHTML = '<div class="activity-modal-empty">No activity recorded yet.</div>';
        return;
      }
      modalList.innerHTML = data.recent.map(activityItemHtml).join('');
    } catch {
      modalList.innerHTML = '<div class="activity-modal-empty">Could not load activity.</div>';
      showToast('Could not load full activity list.', 'error');
    }
  }

  activityModal?.addEventListener('click', e => {
    if (e.target.closest('[data-close-activity-modal]')) closeActivityModal();
  });

  // ── Search ────────────────────────────────────────────────
  const searchInput = document.getElementById('student-search');
  if (searchInput) {
    let t = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(() => loadStudents(searchInput.value.trim()), 400);
    });
  }

  // ── FAB + actions ─────────────────────────────────────────
  document.getElementById('fab-upload')?.addEventListener('click', () => navigate('upload'));
  document.getElementById('add-student-btn')?.addEventListener('click',
    () => showToast('Add Student — not yet implemented.', 'warning'));
  document.getElementById('view-all-activity')?.addEventListener('click', () => openActivityModal());

  await Promise.all([loadSummary(), loadStudents(), loadRecentActivity()]);
});
