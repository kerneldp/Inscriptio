/* ============================================================
   inscriptio — app.js
   Shared state, session helpers, navigation, utilities
   ============================================================ */
'use strict';

// ── Session ───────────────────────────────────────────────────
const Session = {
  save(user)  { sessionStorage.setItem('inscriptio_user', JSON.stringify(user)); },
  get()       {
    try { return JSON.parse(sessionStorage.getItem('inscriptio_user')) || null; }
    catch { return null; }
  },
  clear()     { sessionStorage.removeItem('inscriptio_user'); },
  require()   {
    const user = Session.get();
    if (!user) { window.location.href = '01_authentication_portal.html'; return null; }
    return user;
  },
};

// ── Navigation ────────────────────────────────────────────────
const Pages = {
  auth:     '01_authentication_portal.html',
  dashboard:'02_main_dashboard.html',
  upload:   '03_upload_processing.html',
  report:   '04_hxai_report_view.html',
  compare:  '05_progress_comparison.html',
  archive:  '06_history_archive.html',
  clinician:'07_clinician_workspace.html',
};

function navigate(page) {
  window.location.href = Pages[page] || page;
}

// ── Sidebar nav ───────────────────────────────────────────────
function initSidebarNav() {
  document.querySelectorAll('.nav-item[data-page]').forEach(item => {
    item.addEventListener('click', () => navigate(item.dataset.page));
  });
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', () => { Session.clear(); navigate('auth'); });
}

// ── Sidebar user chip ─────────────────────────────────────────
function populateSidebarUser() {
  const user = Session.get();
  if (!user) return;
  const el = (id) => document.getElementById(id);
  if (el('sidebar-avatar')) el('sidebar-avatar').textContent = user.initials;
  if (el('sidebar-name'))   el('sidebar-name').textContent   = user.name;
  if (el('sidebar-role'))   el('sidebar-role').textContent   =
    user.role.charAt(0).toUpperCase() + user.role.slice(1);
}

// ── Toast ─────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  document.querySelector('.inscriptio-toast')?.remove();
  const colors = { info:'var(--teal)', success:'var(--teal)', warning:'var(--amber)', error:'var(--danger)' };
  const toast = document.createElement('div');
  toast.className = 'inscriptio-toast';
  toast.style.cssText = `
    position:fixed; bottom:32px; left:50%; transform:translateX(-50%);
    background:var(--ink); color:#fff; padding:12px 22px; border-radius:10px;
    font-family:'Figtree',sans-serif; font-size:0.85rem; font-weight:500;
    border-left:4px solid ${colors[type]||colors.info};
    box-shadow:0 8px 24px rgba(0,0,0,0.25);
    z-index:9999; opacity:0; transition:opacity 0.2s; white-space:nowrap;`;
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; });
  setTimeout(() => { toast.style.opacity='0'; setTimeout(()=>toast.remove(),300); }, 2800);
}

// ── Confirm modal ─────────────────────────────────────────────
function confirmModal(message, onConfirm) {
  const overlay = document.createElement('div');
  overlay.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,0.45);
    display:flex;align-items:center;justify-content:center;
    z-index:9998;font-family:'Figtree',sans-serif;`;
  overlay.innerHTML = `
    <div style="background:#fff;border-radius:14px;padding:32px;max-width:400px;
                width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.2);">
      <p style="font-family:'DM Serif Display',serif;font-size:1.2rem;
                color:var(--ink);margin-bottom:12px;">Are you sure?</p>
      <p style="font-size:0.88rem;color:var(--ghost);line-height:1.6;
                margin-bottom:24px;">${message}</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;">
        <button id="modal-cancel" style="padding:10px 20px;border:1.5px solid var(--rule);
          border-radius:8px;background:#fff;cursor:pointer;font-family:'Figtree',sans-serif;
          font-size:0.85rem;font-weight:600;color:var(--ghost);">Cancel</button>
        <button id="modal-confirm" style="padding:10px 20px;border:none;
          border-radius:8px;background:var(--danger);color:#fff;cursor:pointer;
          font-family:'Figtree',sans-serif;font-size:0.85rem;font-weight:600;">Confirm</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelector('#modal-cancel').addEventListener('click',  () => overlay.remove());
  overlay.querySelector('#modal-confirm').addEventListener('click', () => { overlay.remove(); onConfirm(); });
}

// ── Authenticated fetch ───────────────────────────────────────
// Use instead of fetch() for every API call after login.
function authFetch(url, options = {}) {
  const user = Session.get();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (user?.token) headers['Authorization'] = `Bearer ${user.token}`;
  return fetch(url, { ...options, headers });
}

// ── Authenticated multipart fetch (no Content-Type header) ───
// Use for FormData / file uploads.
function authFetchForm(url, formData) {
  const user = Session.get();
  const headers = {};
  if (user?.token) headers['Authorization'] = `Bearer ${user.token}`;
  return fetch(url, { method: 'POST', headers, body: formData });
}