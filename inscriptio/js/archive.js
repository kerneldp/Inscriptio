/* ============================================================
   inscriptio — archive.js  (06_history_archive.html)
   GET /api/history?student_id=&date=&label=
   Open report: sessionStorage current_report_id → report view
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

function buildHistoryQuery() {
  const params = new URLSearchParams();
  const sid = document.getElementById('archive-student')?.value;
  const dt  = document.getElementById('archive-date')?.value?.trim();
  const lb  = document.getElementById('archive-label')?.value;
  if (sid) params.set('student_id', sid);
  if (dt) params.set('date', dt);
  if (lb) params.set('label', lb);
  const q = params.toString();
  return q ? `?${q}` : '';
}

function formatRowDate(rec) {
  const d = (rec.session_date || rec.created_at || '').split('T')[0];
  return d || '—';
}

function formatScore(rec) {
  if (rec.softmax_score == null) return '—';
  return `${(rec.softmax_score * 100).toFixed(1)}%`;
}

document.addEventListener('DOMContentLoaded', async () => {
  const user = Session.require();
  if (!user) return;
  populateSidebarUser();
  initSidebarNav();

  const tbody = document.getElementById('archive-table-body');
  const empty = document.getElementById('archive-empty');

  async function loadStudents() {
    const sel = document.getElementById('archive-student');
    if (!sel) return;
    try {
      const res  = await authFetch(`${API}/api/students`);
      const data = await res.json();
      sel.innerHTML = '<option value="">All students</option>';
      (data.students || []).forEach((s) => {
        const opt = document.createElement('option');
        opt.value = String(s.id);
        opt.textContent = `${s.name}${s.class ? ' · ' + s.class : ''}`;
        sel.appendChild(opt);
      });
    } catch {
      showToast('Could not load students.', 'error');
    }
  }

  async function loadHistory() {
    if (!tbody) return;
    tbody.innerHTML =
      '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--ghost);">Loading…</td></tr>';
    if (empty) empty.style.display = 'none';

    try {
      const res  = await authFetch(`${API}/api/history${buildHistoryQuery()}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Request failed');

      const rows = data.records || [];
      tbody.innerHTML = '';

      if (!rows.length) {
        tbody.innerHTML = '';
        if (empty) {
          empty.style.display = 'block';
          empty.textContent = 'No screening records match these filters.';
        }
        return;
      }

      if (empty) empty.style.display = 'none';

      rows.forEach((rec) => {
        const tr = document.createElement('tr');
        tr.tabIndex = 0;
        tr.dataset.reportId = String(rec.report_id);
        tr.innerHTML = `
          <td>${rec.report_id}</td>
          <td>${escapeHtml(rec.student_name || '—')}</td>
          <td>${escapeHtml(rec.student_class || '—')}</td>
          <td>${formatRowDate(rec)}</td>
          <td>${formatScore(rec)}</td>
          <td>${escapeHtml(rec.label || '—')}</td>
          <td>${rec.verdict ? escapeHtml(rec.verdict) : '<span style="color:var(--amber)">Pending</span>'}</td>`;
        tr.addEventListener('click', () => {
          sessionStorage.setItem('current_report_id', String(rec.report_id));
          navigate('report');
        });
        tr.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            sessionStorage.setItem('current_report_id', String(rec.report_id));
            navigate('report');
          }
        });
        tbody.appendChild(tr);
      });
    } catch (err) {
      tbody.innerHTML = '';
      showToast(`Could not load archive: ${err.message}`, 'error');
      if (empty) {
        empty.style.display = 'block';
        empty.textContent = 'Could not load records.';
      }
    }
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  document.getElementById('archive-apply')?.addEventListener('click', loadHistory);
  document.getElementById('archive-student')?.addEventListener('change', loadHistory);
  document.getElementById('archive-label')?.addEventListener('change', loadHistory);
  document.getElementById('archive-date')?.addEventListener('change', loadHistory);

  await loadStudents();
  await loadHistory();
});
