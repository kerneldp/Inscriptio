/* ============================================================
   inscriptio — app.js
   Shared application state, session helpers, and navigation
   ============================================================ */

'use strict';

// ── Dummy accounts for prototype testing ─────────────────────
const DUMMY_ACCOUNTS = [
  {
    email:    'educator@inscriptio.edu',
    password: 'educator123',
    role:     'educator',
    name:     'M. Reyes',
    initials: 'MR',
  },
  {
    email:    'clinician@inscriptio.edu',
    password: 'clinician123',
    role:     'clinician',
    name:     'Dr. A. Santos',
    initials: 'AS',
  },
];

// ── Session helpers ───────────────────────────────────────────
const Session = {
  /** Save user to sessionStorage after login */
  save(user) {
    sessionStorage.setItem('inscriptio_user', JSON.stringify(user));
  },

  /** Retrieve current session user or null */
  get() {
    try {
      return JSON.parse(sessionStorage.getItem('inscriptio_user')) || null;
    } catch {
      return null;
    }
  },

  /** Clear session (logout) */
  clear() {
    sessionStorage.removeItem('inscriptio_user');
  },

  /** Require auth — redirect to login if not logged in */
  require() {
    const user = Session.get();
    if (!user) {
      window.location.href = '01_authentication_portal.html';
      return null;
    }
    return user;
  },
};

// ── Navigation ────────────────────────────────────────────────
const Pages = {
  auth:      '01_authentication_portal.html',
  dashboard: '02_main_dashboard.html',
  upload:    '03_upload_processing.html',
  report:    '04_hxai_report_view.html',
};

function navigate(page) {
  window.location.href = Pages[page] || page;
}

// ── Sidebar nav wiring (called on each interior page) ─────────
function initSidebarNav() {
  const items = document.querySelectorAll('.nav-item[data-page]');
  items.forEach(item => {
    item.addEventListener('click', () => {
      const page = item.dataset.page;
      navigate(page);
    });
  });

  // Logout
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      Session.clear();
      navigate('auth');
    });
  }
}

// ── Populate sidebar user chip from session ───────────────────
function populateSidebarUser() {
  const user = Session.get();
  if (!user) return;

  const avatarEl  = document.getElementById('sidebar-avatar');
  const nameEl    = document.getElementById('sidebar-name');
  const roleEl    = document.getElementById('sidebar-role');

  if (avatarEl)  avatarEl.textContent  = user.initials;
  if (nameEl)    nameEl.textContent    = user.name;
  if (roleEl)    roleEl.textContent    = user.role.charAt(0).toUpperCase() + user.role.slice(1);
}

// ── Toast notification ────────────────────────────────────────
function showToast(message, type = 'info') {
  const existing = document.querySelector('.inscriptio-toast');
  if (existing) existing.remove();

  const colors = {
    info:    'var(--teal)',
    success: 'var(--teal)',
    warning: 'var(--amber)',
    error:   'var(--danger)',
  };

  const toast = document.createElement('div');
  toast.className = 'inscriptio-toast';
  toast.style.cssText = `
    position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%);
    background: var(--ink); color: #fff;
    padding: 12px 22px; border-radius: 10px;
    font-family: 'Figtree', sans-serif; font-size: 0.85rem; font-weight: 500;
    border-left: 4px solid ${colors[type] || colors.info};
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    z-index: 9999; opacity: 0; transition: opacity 0.2s;
    white-space: nowrap;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(() => { toast.style.opacity = '1'; });
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 2800);
}

// ── Modal confirm ─────────────────────────────────────────────
function confirmModal(message, onConfirm) {
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed; inset: 0; background: rgba(0,0,0,0.45);
    display: flex; align-items: center; justify-content: center;
    z-index: 9998; font-family: 'Figtree', sans-serif;
  `;

  overlay.innerHTML = `
    <div style="background:#fff; border-radius:14px; padding:32px; max-width:400px;
                width:90%; box-shadow:0 20px 60px rgba(0,0,0,0.2);">
      <p style="font-family:'DM Serif Display',serif; font-size:1.2rem;
                color:var(--ink); margin-bottom:12px;">Are you sure?</p>
      <p style="font-size:0.88rem; color:var(--ghost); line-height:1.6;
                margin-bottom:24px;">${message}</p>
      <div style="display:flex; gap:10px; justify-content:flex-end;">
        <button id="modal-cancel" style="padding:10px 20px; border:1.5px solid var(--rule);
          border-radius:8px; background:#fff; cursor:pointer; font-family:'Figtree',sans-serif;
          font-size:0.85rem; font-weight:600; color:var(--ghost);">Cancel</button>
        <button id="modal-confirm" style="padding:10px 20px; border:none;
          border-radius:8px; background:var(--danger); color:#fff; cursor:pointer;
          font-family:'Figtree',sans-serif; font-size:0.85rem; font-weight:600;">Confirm</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  overlay.querySelector('#modal-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#modal-confirm').addEventListener('click', () => {
    overlay.remove();
    onConfirm();
  });
}
