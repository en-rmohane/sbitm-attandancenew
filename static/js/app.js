// ====================================================================
// EduAttend Pro - Core Application & Authentication Management
// ====================================================================

let currentUser = null;
let currentView = null;

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize Lucide icons
  lucide.createIcons();
  
  // Check if session is already active
  await checkAuthSession();
});

// Toast notification helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'error') iconName = 'alert-circle';

  toast.innerHTML = `
    <i data-lucide="${iconName}" style="width: 18px; height: 18px;"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons({ root: toast });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Quick Login Role Selector
function setQuickLogin(roleKey) {
  document.querySelectorAll('.role-pill-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = Array.from(document.querySelectorAll('.role-pill-btn'))
    .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(roleKey));
  if (activeBtn) activeBtn.classList.add('active');

  const usernameInput = document.getElementById('loginUsername');
  const passwordInput = document.getElementById('loginPassword');

  const logins = {
    'admin': 'admin',
    'ravi': 'ravi',
    'satish': 'satish',
    'sonali': 'sonali',
    'alka': 'alka',
    'khushbu': 'khushbu',
    'ashish': 'ashish',
    'jeet': 'jeet',
    'vinay': 'vinay',
    'pankaj': 'pankaj',
    'bhavesh': 'bhavesh',
    'nilesh': 'nilesh'
  };

  usernameInput.value = logins[roleKey] || roleKey;
  passwordInput.value = '112233';
}

// Check session on page load
async function checkAuthSession() {
  try {
    const res = await fetch('/api/auth/me');
    const data = await res.json();
    if (data.authenticated && data.user) {
      currentUser = data.user;
      renderAppForUser();
    } else {
      showLoginScreen();
    }
  } catch (err) {
    showLoginScreen();
  }
}

// Handle Login Submission
async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value.trim();
  const btn = document.getElementById('btnLogin');

  btn.disabled = true;
  btn.innerHTML = '<span>Signing In...</span>';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Login failed', 'error');
      btn.disabled = false;
      btn.innerHTML = '<span>Sign In to Dashboard</span><i data-lucide="arrow-right"></i>';
      lucide.createIcons();
      return;
    }

    currentUser = data.user;
    showToast(`Welcome back, ${currentUser.name}!`, 'success');
    renderAppForUser();
  } catch (err) {
    showToast('Network error during login', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Sign In to Dashboard</span><i data-lucide="arrow-right"></i>';
    lucide.createIcons();
  }
}

// Render App View based on Role
function renderAppForUser() {
  document.getElementById('loginScreen').style.display = 'none';
  document.getElementById('appScreen').style.display = 'flex';

  // Setup user header info
  document.getElementById('headerUserName').textContent = currentUser.name || currentUser.username;
  document.getElementById('userAvatar').textContent = (currentUser.name || currentUser.username)[0].toUpperCase();

  const roleLabel = currentUser.role === 'admin' ? 'Administrator' : `Faculty (${currentUser.assigned_year || 'Subject Teacher'})`;
  document.getElementById('headerUserRole').textContent = roleLabel;

  const yearBadge = document.getElementById('userYearBadge');
  if (currentUser.role === 'faculty') {
    yearBadge.innerHTML = `<i data-lucide="book-open"></i> ${currentUser.assigned_year || 'Faculty Portal'}`;
    yearBadge.style.display = 'inline-flex';
  } else {
    yearBadge.innerHTML = `<i data-lucide="shield-check"></i> All Years (Admin)`;
    yearBadge.style.display = 'inline-flex';
  }

  buildNavigation();

  // Route to default view
  if (currentUser.role === 'faculty') {
    switchView('faculty-subjects');
  } else {
    switchView('admin-dashboard');
  }
}

// Build Desktop & Mobile Navigation Links
function buildNavigation() {
  const desktopNav = document.getElementById('desktopNav');
  const mobileNavLinks = document.getElementById('mobileNavLinks');

  let navItems = [];
  if (currentUser.role === 'faculty') {
    navItems = [
      { id: 'faculty-subjects', label: 'My Subjects & Labs', icon: 'book-open' },
      { id: 'faculty-mark', label: 'Daily Attendance', icon: 'calendar-check' },
      { id: 'faculty-history', label: 'My Submissions', icon: 'history' },
      { id: 'reports', label: 'Class Reports', icon: 'bar-chart-3' }
    ];
  } else {
    navItems = [
      { id: 'admin-dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
      { id: 'admin-subjects', label: 'Subjects & Allocations', icon: 'book-marked' },
      { id: 'admin-students', label: 'Students', icon: 'users' },
      { id: 'admin-faculty', label: 'Faculty', icon: 'user-check' },
      { id: 'admin-holidays', label: 'Holidays / Leaves', icon: 'calendar-off' },
      { id: 'reports', label: 'Reports & Matrix', icon: 'file-spreadsheet' }
    ];
  }

  const html = navItems.map(item => `
    <button class="nav-link" id="nav-${item.id}" onclick="switchView('${item.id}')">
      <i data-lucide="${item.icon}"></i>
      <span>${item.label}</span>
    </button>
  `).join('');

  desktopNav.innerHTML = html;
  mobileNavLinks.innerHTML = html;
  lucide.createIcons();
}

// Switch Active View
function switchView(viewId) {
  currentView = viewId;

  // Close mobile drawer if open
  document.getElementById('mobileDrawer').classList.remove('open');
  document.getElementById('drawerOverlay').classList.remove('open');

  // Update nav active classes
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.id === `nav-${viewId}`);
  });

  // Hide all views
  document.querySelectorAll('.view-section').forEach(sec => sec.style.display = 'none');

  // Show selected view and trigger its loader
  if (viewId === 'faculty-subjects') {
    document.getElementById('facultySubjectsView').style.display = 'block';
    initFacultySubjectsView();
  } else if (viewId === 'faculty-mark') {
    document.getElementById('facultyMarkView').style.display = 'block';
    initFacultyMarkAttendance();
  } else if (viewId === 'faculty-history') {
    document.getElementById('facultyHistoryView').style.display = 'block';
    loadFacultyHistory();
  } else if (viewId === 'admin-dashboard') {
    document.getElementById('adminDashboardView').style.display = 'block';
    loadAdminDashboard();
  } else if (viewId === 'admin-subjects') {
    document.getElementById('adminSubjectsView').style.display = 'block';
    loadAdminSubjects();
  } else if (viewId === 'admin-students') {
    document.getElementById('adminStudentsView').style.display = 'block';
    loadAdminStudents();
  } else if (viewId === 'admin-faculty') {
    document.getElementById('adminFacultyView').style.display = 'block';
    loadAdminFaculty();
  } else if (viewId === 'admin-holidays') {
    document.getElementById('adminHolidaysView').style.display = 'block';
    loadAdminHolidays();
  } else if (viewId === 'reports') {
    document.getElementById('reportsView').style.display = 'block';
    initReportsView();
  }

  lucide.createIcons();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

  lucide.createIcons();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Toggle Mobile Drawer
function toggleMobileNav() {
  const drawer = document.getElementById('mobileDrawer');
  const overlay = document.getElementById('drawerOverlay');
  const isOpen = drawer.classList.contains('open');
  if (isOpen) {
    drawer.classList.remove('open');
    overlay.classList.remove('open');
  } else {
    drawer.classList.add('open');
    overlay.classList.add('open');
  }
}

// Logout
async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  currentUser = null;
  showLoginScreen();
  showToast('Logged out successfully', 'info');
}

function showLoginScreen() {
  document.getElementById('appScreen').style.display = 'none';
  document.getElementById('loginScreen').style.display = 'flex';
  setQuickLogin('admin');
}
