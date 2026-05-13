/* ============================================================
   inscriptio — auth.js
   Logic for 01_authentication_portal.html
   POST /api/auth/login
   ============================================================ */
'use strict';

const API = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
  if (Session.get()) { navigate('dashboard'); return; }

  const tabLogin     = document.getElementById('tab-login');
  const tabSignup    = document.getElementById('tab-signup');
  const signupFields = document.getElementById('signup-fields');
  const roleBtns     = document.querySelectorAll('.role-btn');
  const emailInput   = document.getElementById('email');
  const passwordInput= document.getElementById('password');
  const submitBtn    = document.getElementById('submit-btn');
  const submitLabel  = document.getElementById('submit-label');
  const authError    = document.getElementById('auth-error');
  const nameInput    = document.getElementById('full-name');
  const confirmInput = document.getElementById('confirm-password');
  const demoItems    = document.querySelectorAll('.demo-account');

  let activeTab  = 'login';
  let activeRole = 'educator';

  // ── Tab switching ─────────────────────────────────────────
  function setTab(tab) {
    activeTab = tab;
    tabLogin.classList.toggle('active',  tab === 'login');
    tabSignup.classList.toggle('active', tab === 'signup');
    signupFields?.classList.toggle('visible', tab === 'signup');
    submitLabel.textContent = tab === 'login' ? 'Sign In to Dashboard' : 'Create Account';
    clearError();
  }

  tabLogin?.addEventListener('click',  () => setTab('login'));
  tabSignup?.addEventListener('click', () => setTab('signup'));

  // ── Role toggle ───────────────────────────────────────────
  roleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      activeRole = btn.dataset.role;
      roleBtns.forEach(b => b.classList.toggle('active', b.dataset.role === activeRole));
    });
  });

  // ── Demo account auto-fill ────────────────────────────────
  demoItems.forEach(item => {
    item.addEventListener('click', () => {
      emailInput.value     = item.dataset.email;
      passwordInput.value  = item.dataset.password;
      activeRole           = item.dataset.role;
      roleBtns.forEach(b => b.classList.toggle('active', b.dataset.role === activeRole));
      setTab('login');
      showToast('Demo account filled — click Sign In', 'info');
    });
  });

  // ── Error helpers ─────────────────────────────────────────
  function showError(msg) {
    if (!authError) return;
    authError.textContent = msg;
    authError.classList.add('visible');
  }
  function clearError() { authError?.classList.remove('visible'); }

  // ── Login ─────────────────────────────────────────────────
  async function handleLogin() {
    clearError();
    const email    = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;
    if (!email || !password) { showError('Please enter your email and password.'); return; }

    submitBtn.disabled      = true;
    submitLabel.textContent = 'Signing in…';

    try {
      const res  = await fetch(`${API}/api/auth/login`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email, password, role: activeRole }),
      });
      const data = await res.json();

      if (!res.ok) { showError(data.detail || 'Incorrect email or password.'); return; }

      Session.save({ ...data.user, token: data.token });
      showToast(`Welcome back, ${data.user.name}!`, 'success');
      const dest = data.user.role === 'clinician' ? 'clinician' : 'dashboard';
      setTimeout(() => navigate(dest), 600);

    } catch {
      showError('Cannot connect to server. Make sure the backend is running.');
    } finally {
      submitBtn.disabled      = false;
      submitLabel.textContent = 'Sign In to Dashboard';
    }
  }

  // ── Signup (disabled for demo) ────────────────────────────
  function handleSignup() {
    clearError();
    showError('Registration is disabled for demo. Please use a demo account below.');
  }

  submitBtn.addEventListener('click', () => {
    if (activeTab === 'login') handleLogin(); else handleSignup();
  });

  [emailInput, passwordInput, nameInput, confirmInput].forEach(el => {
    el?.addEventListener('keydown', e => { if (e.key === 'Enter') submitBtn.click(); });
  });
});