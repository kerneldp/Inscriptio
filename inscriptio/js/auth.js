/* ============================================================
   inscriptio — auth.js
   Logic for 01_authentication_portal.html
   DEV NOTE: Replace DUMMY_ACCOUNTS logic with POST /api/auth/login
   and POST /api/auth/register. JWT response stored in session.
   ============================================================ */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  // If already logged in, go straight to dashboard
  if (Session.get()) {
    navigate('dashboard');
    return;
  }

  // ── Element refs ──────────────────────────────────────────
  const tabLogin  = document.getElementById('tab-login');
  const tabSignup = document.getElementById('tab-signup');
  const signupFields = document.getElementById('signup-fields');

  const roleBtns  = document.querySelectorAll('.role-btn');
  const emailInput    = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const submitBtn     = document.getElementById('submit-btn');
  const submitLabel   = document.getElementById('submit-label');
  const authError     = document.getElementById('auth-error');

  // Signup-only
  const nameInput     = document.getElementById('full-name');
  const confirmInput  = document.getElementById('confirm-password');

  // Demo accounts
  const demoItems = document.querySelectorAll('.demo-account');

  let activeTab  = 'login';
  let activeRole = 'educator';

  // ── Tab switching ─────────────────────────────────────────
  function setTab(tab) {
    activeTab = tab;
    tabLogin.classList.toggle('active', tab === 'login');
    tabSignup.classList.toggle('active', tab === 'signup');
    signupFields.classList.toggle('visible', tab === 'signup');

    submitLabel.textContent = tab === 'login'
      ? 'Sign In to Dashboard'
      : 'Create Account';
    clearError();
  }

  tabLogin.addEventListener('click',  () => setTab('login'));
  tabSignup.addEventListener('click', () => setTab('signup'));

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
      const email = item.dataset.email;
      const pass  = item.dataset.password;
      const role  = item.dataset.role;

      emailInput.value    = email;
      passwordInput.value = pass;

      // Switch role button
      activeRole = role;
      roleBtns.forEach(b => b.classList.toggle('active', b.dataset.role === activeRole));

      // Make sure we're on login tab
      setTab('login');

      showToast(`Demo account filled — click Sign In`, 'info');
    });
  });

  // ── Error helpers ─────────────────────────────────────────
  function showError(msg) {
    authError.textContent = msg;
    authError.classList.add('visible');
  }

  function clearError() {
    authError.classList.remove('visible');
  }

  // ── Login logic ───────────────────────────────────────────
  function handleLogin() {
    clearError();
    const email    = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;

    if (!email || !password) {
      showError('Please enter your email and password.');
      return;
    }

    // DEV NOTE: Replace with POST /api/auth/login { email, password, role }
    const match = DUMMY_ACCOUNTS.find(
      a => a.email === email && a.password === password
    );

    if (!match) {
      showError('Incorrect email or password. Try a demo account below.');
      return;
    }

    // Role override — allow role selection to affect dummy account UX
    const user = { ...match, role: activeRole };
    Session.save(user);
    showToast(`Welcome back, ${user.name}!`, 'success');
    setTimeout(() => navigate('dashboard'), 600);
  }

  // ── Signup logic ──────────────────────────────────────────
  function handleSignup() {
    clearError();
    const name     = nameInput ? nameInput.value.trim() : '';
    const email    = emailInput.value.trim().toLowerCase();
    const password = passwordInput.value;
    const confirm  = confirmInput ? confirmInput.value : '';

    if (!name || !email || !password || !confirm) {
      showError('Please fill in all fields.');
      return;
    }

    if (password !== confirm) {
      showError('Passwords do not match.');
      return;
    }

    if (password.length < 8) {
      showError('Password must be at least 8 characters.');
      return;
    }

    // DEV NOTE: Replace with POST /api/auth/register { name, email, password, role }
    // For prototype: pretend signup succeeds, create a session with the new account
    const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    const user = { email, role: activeRole, name, initials };
    Session.save(user);
    showToast(`Account created! Welcome, ${name}.`, 'success');
    setTimeout(() => navigate('dashboard'), 600);
  }

  // ── Submit button ─────────────────────────────────────────
  submitBtn.addEventListener('click', () => {
    if (activeTab === 'login') handleLogin();
    else handleSignup();
  });

  // Allow Enter key on inputs
  [emailInput, passwordInput, nameInput, confirmInput].forEach(el => {
    if (!el) return;
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter') submitBtn.click();
    });
  });
});
