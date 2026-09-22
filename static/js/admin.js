// ====================================================================
// EduAttend Pro - Admin Management Module (Students, Faculty, Holidays, Logs)
// ====================================================================

let allStudentsList = [];
let selectedImportFile = null;

// 1. ADMIN DASHBOARD
async function loadAdminDashboard() {
  try {
    const res = await fetch('/api/admin/dashboard');
    const data = await res.json();

    document.getElementById('dashTodayDate').textContent = data.today_date || 'Today';
    document.getElementById('dashTotalStudents').textContent = data.total_students || 0;
    
    // Support both specific IDs and dynamic counts
    const yCounts = data.year_counts || {};
    const el2 = document.getElementById('dash2ndYearStudents');
    if (el2) el2.textContent = yCounts['2nd Year (CSE)'] || yCounts['2nd Year'] || 0;
    const el3 = document.getElementById('dash3rdYearStudents');
    if (el3) el3.textContent = yCounts['3rd Year (CSE)'] || yCounts['3rd Year'] || 0;
    const el4 = document.getElementById('dash4thYearStudents');
    if (el4) el4.textContent = yCounts['4th Year (CSE)'] || yCounts['4th Year'] || 0;
    const el4aids = document.getElementById('dash4thAidsStudents');
    if (el4aids) el4aids.textContent = yCounts['4th Year (AI-DS)'] || 0;

    // Render Today's Status Cards for all active classes
    const statusContainer = document.getElementById('todayStatusCards');
    const classes = Object.keys(data.today_status || {});
    statusContainer.innerHTML = classes.map(yr => {
      const info = data.today_status[yr] || { status: 'Pending' };
      const isSubmitted = info.status === 'Submitted';

      return `
        <div class="today-status-card">
          <div>
            <div class="year-title">${yr}</div>
            <div style="font-size: 12px; color: var(--slate-500); margin-top: 4px;">
              ${isSubmitted ? `Submitted by ${info.faculty}` : 'Attendance not submitted yet'}
            </div>
            ${isSubmitted ? `<div style="font-size: 11px; color: var(--slate-400);">${info.submitted_at}</div>` : ''}
          </div>
          <div>
            <span class="status-badge ${isSubmitted ? 'status-submitted' : 'status-pending'}">
              <i data-lucide="${isSubmitted ? 'check-circle-2' : 'clock'}" style="width: 14px; height: 14px;"></i>
              ${info.status}
            </span>
          </div>
        </div>
      `;
    }).join('');

    // Render Recent Submissions
    const tbody = document.getElementById('dashRecentSubsTable');
    if (!data.recent_submissions || data.recent_submissions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--slate-500);">No attendance submissions found yet.</td></tr>`;
    } else {
      tbody.innerHTML = data.recent_submissions.map(sub => `
        <tr>
          <td><span class="count-pill">${sub.year}</span></td>
          <td><strong>${sub.date}</strong></td>
          <td>${sub.faculty_name || 'Faculty'}</td>
          <td style="color: var(--slate-500);">${sub.submitted_at || '-'}</td>
          <td>${sub.student_count || 0}</td>
          <td>
            <span class="status-badge status-submitted">${sub.present_count || 0} P</span>
            <span class="status-badge status-pending">${sub.absent_count || 0} A</span>
          </td>
          <td>
            <button class="btn btn-outline btn-xs" onclick="openAttendanceEditModal(${sub.id}, '${sub.year}', '${sub.date}')">
              <i data-lucide="edit-3"></i> View / Edit
            </button>
          </td>
        </tr>
      `).join('');
    }

    lucide.createIcons();
  } catch (err) {
    showToast('Failed to load admin dashboard', 'error');
  }
}

// 2. STUDENT MANAGEMENT
async function loadAdminStudents() {
  try {
    const res = await fetch('/api/admin/students');
    const data = await res.json();
    allStudentsList = data.students || [];
    filterStudentsList();
  } catch (err) {
    showToast('Failed to fetch students', 'error');
  }
}

function filterStudentsList() {
  const searchTerm = document.getElementById('studentSearchInput').value.toLowerCase();
  const yearFilter = document.getElementById('studentYearFilter').value;
  const statusFilter = document.getElementById('studentStatusFilter').value;

  const filtered = allStudentsList.filter(s => {
    const matchesSearch = !searchTerm ||
      (s.name && s.name.toLowerCase().includes(searchTerm)) ||
      (s.roll_no && s.roll_no.toLowerCase().includes(searchTerm)) ||
      (s.enrollment_no && s.enrollment_no.toLowerCase().includes(searchTerm));

    const matchesYear = !yearFilter || s.year === yearFilter;
    const matchesStatus = !statusFilter || s.status === statusFilter;

    return matchesSearch && matchesYear && matchesStatus;
  });

  renderStudentsTable(filtered);
}

function renderStudentsTable(students) {
  const tbody = document.getElementById('studentsTableBody');
  if (students.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 32px; color: var(--slate-500);">No students match your filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = students.map(s => `
    <tr>
      <td><strong>${s.roll_no}</strong></td>
      <td>
        <div style="font-weight: 600;">${s.name}</div>
      </td>
      <td style="color: var(--slate-600);">${s.enrollment_no || '-'}</td>
      <td><span class="count-pill">${s.year}</span></td>
      <td>
        <span class="status-badge ${s.status === 'active' ? 'status-submitted' : 'status-pending'}">
          ${s.status === 'active' ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td style="text-align: right;">
        <button class="btn-icon" title="Edit Student" onclick="openEditStudentModal(${s.id})">
          <i data-lucide="edit"></i>
        </button>
        <button class="btn-icon" title="Delete Student" style="color: var(--danger);" onclick="deleteStudent(${s.id}, '${s.name}')">
          <i data-lucide="trash-2"></i>
        </button>
      </td>
    </tr>
  `).join('');

  lucide.createIcons();
}

function openAddStudentModal() {
  document.getElementById('studentModalTitle').textContent = 'Add New Student';
  document.getElementById('studentEditId').value = '';
  document.getElementById('modalStudentRoll').value = '';
  document.getElementById('modalStudentName').value = '';
  document.getElementById('modalStudentEnrollment').value = '';
  document.getElementById('modalStudentYear').value = '2nd Year';
  document.getElementById('modalStudentStatus').value = 'active';
  document.getElementById('studentModal').style.display = 'flex';
}

function openEditStudentModal(studentId) {
  const student = allStudentsList.find(s => s.id === studentId);
  if (!student) return;

  document.getElementById('studentModalTitle').textContent = 'Edit Student Details';
  document.getElementById('studentEditId').value = student.id;
  document.getElementById('modalStudentRoll').value = student.roll_no;
  document.getElementById('modalStudentName').value = student.name;
  document.getElementById('modalStudentEnrollment').value = student.enrollment_no || '';
  document.getElementById('modalStudentYear').value = student.year;
  document.getElementById('modalStudentStatus').value = student.status;
  document.getElementById('studentModal').style.display = 'flex';
}

function closeStudentModal() {
  document.getElementById('studentModal').style.display = 'none';
}

async function handleSaveStudent(e) {
  e.preventDefault();
  const id = document.getElementById('studentEditId').value;
  const roll_no = document.getElementById('modalStudentRoll').value.trim();
  const name = document.getElementById('modalStudentName').value.trim();
  const enrollment_no = document.getElementById('modalStudentEnrollment').value.trim();
  const year = document.getElementById('modalStudentYear').value;
  const status = document.getElementById('modalStudentStatus').value;

  const url = id ? `/api/admin/students/${id}` : '/api/admin/students';
  const method = id ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roll_no, name, enrollment_no, year, status })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to save student', 'error');
      return;
    }
    showToast(data.message || 'Saved successfully', 'success');
    closeStudentModal();
    loadAdminStudents();
  } catch (err) {
    showToast('Network error while saving student', 'error');
  }
}

async function deleteStudent(studentId, name) {
  if (!confirm(`Are you sure you want to delete student "${name}"? This will also remove their attendance history.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/admin/students/${studentId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to delete student', 'error');
      return;
    }
    showToast('Student deleted successfully', 'success');
    loadAdminStudents();
  } catch (err) {
    showToast('Network error while deleting student', 'error');
  }
}

// 3. BULK EXCEL/CSV IMPORT
function openImportStudentsModal() {
  selectedImportFile = null;
  document.getElementById('importFileName').textContent = 'Click or drop Excel / CSV file here';
  document.getElementById('importFileInput').value = '';
  document.getElementById('importModal').style.display = 'flex';
}

function closeImportModal() {
  document.getElementById('importModal').style.display = 'none';
}

function onImportFileSelected(event) {
  const file = event.target.files[0];
  if (file) {
    selectedImportFile = file;
    document.getElementById('importFileName').innerHTML = `Selected: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  }
}

async function uploadStudentsFile() {
  if (!selectedImportFile) {
    showToast('Please choose an Excel or CSV file first', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedImportFile);

  const btn = document.getElementById('btnUploadStudents');
  btn.disabled = true;
  btn.textContent = 'Importing...';

  try {
    const res = await fetch('/api/admin/students/import', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Import failed', 'error');
      return;
    }

    showToast(data.message || 'Students imported successfully', 'success');
    closeImportModal();
    loadAdminStudents();
  } catch (err) {
    showToast('Error uploading file', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload & Import';
  }
}

function downloadSampleCSV() {
  const csvContent = "data:text/csv;charset=utf-8," + 
    "Roll No,Student Name,Year,Enrollment No\n" +
    "01,Rahul Kumar,2nd Year,EN202401\n" +
    "02,Amit Patel,2nd Year,EN202402\n" +
    "01,Aarav Mehta,3rd Year,EN202301\n" +
    "01,Aditya Chopra,4th Year,EN202201\n";
  
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "sample_students_template.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// 4. FACULTY MANAGEMENT
async function loadAdminFaculty() {
  try {
    const res = await fetch('/api/admin/faculty');
    const data = await res.json();
    const faculties = data.faculty || [];

    const container = document.getElementById('facultyCardsGrid');
    container.innerHTML = faculties.map(f => `
      <div class="faculty-card">
        <div class="faculty-assigned-tag">${f.assigned_year}</div>
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 16px;">
          <div class="avatar-circle" style="width: 48px; height: 48px; font-size: 18px;">${f.name[0]}</div>
          <div>
            <h3 style="font-size: 16px;">${f.name}</h3>
            <span style="font-size: 12px; color: var(--slate-500);">Username: <code>${f.username || 'faculty'}</code></span>
          </div>
        </div>
        <div style="font-size: 13px; color: var(--slate-700); margin-bottom: 8px;">
          <i data-lucide="mail" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 4px;"></i> ${f.email}
        </div>
        <div style="font-size: 13px; color: var(--slate-700); margin-bottom: 16px;">
          <i data-lucide="phone" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 4px;"></i> ${f.phone || 'Not provided'}
        </div>
        <button class="btn btn-outline btn-block btn-sm" onclick='openEditFacultyModal(${JSON.stringify(f)})'>
          <i data-lucide="settings"></i> Edit Faculty / Reassign Year
        </button>
      </div>
    `).join('');

    lucide.createIcons();
  } catch (err) {
    showToast('Failed to load faculty list', 'error');
  }
}

function openEditFacultyModal(faculty) {
  document.getElementById('facultyEditId').value = faculty.id;
  document.getElementById('modalFacultyName').value = faculty.name;
  document.getElementById('modalFacultyEmail').value = faculty.email;
  document.getElementById('modalFacultyPhone').value = faculty.phone || '';
  document.getElementById('modalFacultyYear').value = faculty.assigned_year;
  document.getElementById('modalFacultyPass').value = '';
  document.getElementById('facultyModal').style.display = 'flex';
}

function closeFacultyModal() {
  document.getElementById('facultyModal').style.display = 'none';
}

async function handleSaveFaculty(e) {
  e.preventDefault();
  const id = document.getElementById('facultyEditId').value;
  const name = document.getElementById('modalFacultyName').value.trim();
  const email = document.getElementById('modalFacultyEmail').value.trim();
  const phone = document.getElementById('modalFacultyPhone').value.trim();
  const assigned_year = document.getElementById('modalFacultyYear').value;
  const password = document.getElementById('modalFacultyPass').value.trim();

  try {
    const res = await fetch(`/api/admin/faculty/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, phone, assigned_year, password })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to update faculty', 'error');
      return;
    }
    showToast('Faculty details updated successfully', 'success');
    closeFacultyModal();
    loadAdminFaculty();
  } catch (err) {
    showToast('Network error while saving faculty', 'error');
  }
}

// 5. HOLIDAY MANAGEMENT
async function loadAdminHolidays() {
  try {
    const res = await fetch('/api/admin/holidays');
    const data = await res.json();
    const holidays = data.holidays || [];

    const tbody = document.getElementById('holidaysTableBody');
    if (holidays.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 28px; color: var(--slate-500);">No holidays added yet.</td></tr>`;
      return;
    }

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    tbody.innerHTML = holidays.map(h => {
      const dt = new Date(h.date + 'T00:00:00');
      const dayName = isNaN(dt.getDay()) ? '-' : days[dt.getDay()];

      return `
        <tr>
          <td><strong>${h.date}</strong></td>
          <td><span class="count-pill">${dayName}</span></td>
          <td>${h.reason}</td>
          <td style="text-align: right;">
            <button class="btn-icon" style="color: var(--danger);" title="Delete Holiday" onclick="deleteHoliday(${h.id}, '${h.date}')">
              <i data-lucide="trash-2"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    showToast('Failed to load holidays', 'error');
  }
}

function openAddHolidayModal() {
  document.getElementById('modalHolidayDate').value = '';
  document.getElementById('modalHolidayReason').value = '';
  document.getElementById('holidayModal').style.display = 'flex';
}

function closeHolidayModal() {
  document.getElementById('holidayModal').style.display = 'none';
}

async function handleSaveHoliday(e) {
  e.preventDefault();
  const date = document.getElementById('modalHolidayDate').value;
  const reason = document.getElementById('modalHolidayReason').value.trim();

  try {
    const res = await fetch('/api/admin/holidays', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, reason })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to add holiday', 'error');
      return;
    }
    showToast('Holiday added successfully', 'success');
    closeHolidayModal();
    loadAdminHolidays();
  } catch (err) {
    showToast('Network error while saving holiday', 'error');
  }
}

async function deleteHoliday(holidayId, dateStr) {
  if (!confirm(`Delete holiday on ${dateStr}?`)) return;
  try {
    const res = await fetch(`/api/admin/holidays/${holidayId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to delete holiday', 'error');
      return;
    }
    showToast('Holiday deleted successfully', 'success');
    loadAdminHolidays();
  } catch (err) {
    showToast('Network error deleting holiday', 'error');
  }
}

// 6. ATTENDANCE EDIT MODAL FOR ADMIN
async function openAttendanceEditModal(attendanceId, year, date) {
  document.getElementById('editAttendanceId').value = attendanceId;
  document.getElementById('attendanceEditModalSubtitle').textContent = `${year} — Date: ${date}`;
  const tbody = document.getElementById('attendanceEditTableBody');
  tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 24px; color: var(--slate-500);"><i data-lucide="loader" class="spin"></i> Loading student records...</td></tr>`;
  document.getElementById('attendanceEditModal').style.display = 'flex';
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch(`/api/admin/attendance-detail/${attendanceId}`);
    let data;
    try {
      data = await res.json();
    } catch (e) {
      data = { error: `Server error (${res.status})` };
    }
    
    if (res.status === 401) {
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 24px; color: var(--rose-500);">Session expired. Please <a href="javascript:void(0)" onclick="location.reload()" style="color: var(--brand-600); font-weight: 600; text-decoration: underline;">log in again</a>.</td></tr>`;
      showToast('Session expired. Please log in again.', 'error');
      return;
    }

    if (!res.ok) {
      const errMsg = data.error || `Failed to load attendance detail (${res.status})`;
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 24px; color: var(--rose-500);">${errMsg} <br><button class="btn btn-outline btn-xs" style="margin-top: 8px;" onclick="openAttendanceEditModal(${attendanceId}, '${year}', '${date}')">Retry</button></td></tr>`;
      showToast(errMsg, 'error');
      return;
    }

    const records = data.records || [];
    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 24px; color: var(--slate-500);">No student records found for this attendance session.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(r => `
      <tr>
        <td><strong>${r.roll_no}</strong></td>
        <td>${r.name}</td>
        <td style="text-align: center;">
          <select class="input-select admin-att-select" data-student-id="${r.student_id}">
            <option value="Present" ${r.status === 'Present' ? 'selected' : ''}>Present</option>
            <option value="Absent" ${r.status === 'Absent' ? 'selected' : ''}>Absent</option>
          </select>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 24px; color: var(--rose-500);">Error loading attendance details. <br><button class="btn btn-outline btn-xs" style="margin-top: 8px;" onclick="openAttendanceEditModal(${attendanceId}, '${year}', '${date}')">Retry</button></td></tr>`;
    showToast('Failed to load attendance detail', 'error');
  }
}

function closeAttendanceEditModal() {
  document.getElementById('attendanceEditModal').style.display = 'none';
}

async function saveEditedAttendance() {
  const attendanceId = document.getElementById('editAttendanceId').value;
  const selects = document.querySelectorAll('.admin-att-select');
  const records = [];

  selects.forEach(sel => {
    records.push({
      student_id: parseInt(sel.dataset.studentId),
      status: sel.value
    });
  });

  try {
    const res = await fetch(`/api/admin/attendance-detail/${attendanceId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to update attendance', 'error');
      return;
    }
    showToast('Attendance updated successfully!', 'success');
    closeAttendanceEditModal();
    loadAdminDashboard();
  } catch (err) {
    showToast('Network error while updating attendance', 'error');
  }
}

// ====================================================================
// 3. ADMIN SUBJECT & ALLOCATION MANAGEMENT
// ====================================================================

let allAdminSubjects = [];
let allFacultyCache = [];

async function loadAdminSubjects() {
  const tbody = document.getElementById('adminSubjectsTableBody');
  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px;">Loading subjects catalog...</td></tr>`;

  try {
    const [subRes, facRes] = await Promise.all([
      fetch('/api/admin/subjects'),
      fetch('/api/admin/faculty')
    ]);

    const subData = await subRes.json();
    const facData = await facRes.json();

    allAdminSubjects = subData.subjects || [];
    allFacultyCache = facData.faculty || [];

    filterAdminSubjects();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger);">Failed to load subjects.</td></tr>`;
    showToast('Failed to load subjects catalog', 'error');
  }
}

function filterAdminSubjects() {
  const search = (document.getElementById('adminSubjSearchInput')?.value || '').toLowerCase();
  const dept = document.getElementById('adminSubjDeptFilter')?.value || '';
  const sem = document.getElementById('adminSubjSemFilter')?.value || '';
  const type = document.getElementById('adminSubjTypeFilter')?.value || '';

  const filtered = allAdminSubjects.filter(s => {
    const matchSearch = !search || s.code.toLowerCase().includes(search) || s.name.toLowerCase().includes(search) || (s.faculty_names || '').toLowerCase().includes(search);
    const matchDept = !dept || s.department === dept;
    const matchSem = !sem || s.semester === sem;
    const matchType = !type || s.type === type;
    return matchSearch && matchDept && matchSem && matchType;
  });

  const tbody = document.getElementById('adminSubjectsTableBody');
  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 32px; color: var(--slate-500);">No matching subjects found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => {
    const isLab = s.type === 'Practical';
    const typeBadge = isLab ? 'badge-purple' : 'badge-indigo';
    const deptBadge = s.department === 'AI-DS' ? 'badge-amber' : 'badge-sky';

    return `
      <tr>
        <td><strong>${s.code}</strong></td>
        <td>
          <div style="font-weight: 600; color: var(--slate-900);">${s.name}</div>
        </td>
        <td><span class="badge ${typeBadge}">${s.type}</span></td>
        <td><span class="badge ${deptBadge}">${s.department} (${s.semester} Sem)</span></td>
        <td><span class="badge badge-slate">${s.year}</span></td>
        <td>
          <div style="font-weight: 500; color: var(--slate-800);">${s.faculty_names || '<span style="color: var(--slate-400);">Unallocated</span>'}</div>
        </td>
        <td style="text-align: right;">
          <button class="btn btn-outline-primary btn-xs" onclick="openAllocateModal(${s.id})" title="Allocate Faculty">
            <i data-lucide="user-plus"></i> Allocate
          </button>
          <button class="btn btn-outline btn-xs" onclick="openEditSubjectModal(${s.id})" title="Edit Subject">
            <i data-lucide="edit"></i>
          </button>
          <button class="btn btn-outline-danger btn-xs" onclick="deleteSubject(${s.id})" title="Delete Subject">
            <i data-lucide="trash-2"></i>
          </button>
        </td>
      </tr>
    `;
  }).join('');

  lucide.createIcons();
}

function openAddSubjectModal() {
  document.getElementById('subjectEditId').value = '';
  document.getElementById('subjectModalTitle').textContent = 'Add New Subject';
  document.getElementById('modalSubjectCode').value = '';
  document.getElementById('modalSubjectName').value = '';
  document.getElementById('modalSubjectType').value = 'Theory';
  document.getElementById('modalSubjectDept').value = 'CSE';
  document.getElementById('modalSubjectSem').value = 'III';
  document.getElementById('modalSubjectYear').value = '2nd Year (CSE)';

  document.getElementById('subjectModal').style.display = 'flex';
  lucide.createIcons();
}

function openEditSubjectModal(subjectId) {
  const s = allAdminSubjects.find(x => x.id === subjectId);
  if (!s) return;

  document.getElementById('subjectEditId').value = s.id;
  document.getElementById('subjectModalTitle').textContent = `Edit Subject: ${s.code}`;
  document.getElementById('modalSubjectCode').value = s.code;
  document.getElementById('modalSubjectName').value = s.name;
  document.getElementById('modalSubjectType').value = s.type;
  document.getElementById('modalSubjectDept').value = s.department;
  document.getElementById('modalSubjectSem').value = s.semester;
  document.getElementById('modalSubjectYear').value = s.year;

  document.getElementById('subjectModal').style.display = 'flex';
  lucide.createIcons();
}

function closeSubjectModal() {
  document.getElementById('subjectModal').style.display = 'none';
}

async function handleSaveSubject(e) {
  e.preventDefault();
  const id = document.getElementById('subjectEditId').value;
  const code = document.getElementById('modalSubjectCode').value.trim();
  const name = document.getElementById('modalSubjectName').value.trim();
  const type = document.getElementById('modalSubjectType').value;
  const department = document.getElementById('modalSubjectDept').value;
  const semester = document.getElementById('modalSubjectSem').value;
  const year = document.getElementById('modalSubjectYear').value;

  const url = id ? `/api/admin/subjects/${id}` : '/api/admin/subjects';
  const method = id ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, name, type, department, semester, year })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to save subject', 'error');
      return;
    }

    showToast(`Subject ${code} saved successfully!`, 'success');
    closeSubjectModal();
    loadAdminSubjects();
  } catch (err) {
    showToast('Network error while saving subject', 'error');
  }
}

async function deleteSubject(subjectId) {
  const s = allAdminSubjects.find(x => x.id === subjectId);
  if (!confirm(`Are you sure you want to delete subject "${s?.code} - ${s?.name}"?`)) return;

  try {
    const res = await fetch(`/api/admin/subjects/${subjectId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to delete subject', 'error');
      return;
    }
    showToast('Subject deleted successfully', 'success');
    loadAdminSubjects();
  } catch (err) {
    showToast('Network error while deleting subject', 'error');
  }
}

function openAllocateModal(subjectId) {
  const s = allAdminSubjects.find(x => x.id === subjectId);
  if (!s) return;

  document.getElementById('allocSubjectId').value = s.id;
  document.getElementById('allocModalTitle').textContent = 'Allocate Faculty to Subject';
  document.getElementById('allocModalSubtitle').textContent = `${s.code}: ${s.name} (${s.type} - ${s.year})`;

  const listContainer = document.getElementById('allocFacultyCheckboxList');
  const currentFacultyIds = s.faculty_ids || [];

  listContainer.innerHTML = allFacultyCache.map(f => {
    const isChecked = currentFacultyIds.includes(f.id);
    return `
      <label style="display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: 6px; cursor: pointer; background: ${isChecked ? 'var(--slate-50)' : 'transparent'};">
        <input type="checkbox" class="alloc-faculty-cb" value="${f.id}" ${isChecked ? 'checked' : ''} style="width: 16px; height: 16px; cursor: pointer;">
        <div>
          <div style="font-weight: 600; font-size: 13.5px; color: var(--slate-900);">${f.name}</div>
          <div style="font-size: 11.5px; color: var(--slate-500);">${f.email} | ${f.assigned_year}</div>
        </div>
      </label>
    `;
  }).join('');

  document.getElementById('allocateFacultyModal').style.display = 'flex';
  lucide.createIcons();
}

function closeAllocateModal() {
  document.getElementById('allocateFacultyModal').style.display = 'none';
}

async function handleSaveAllocation(e) {
  e.preventDefault();
  const subjectId = document.getElementById('allocSubjectId').value;
  const checkboxes = document.querySelectorAll('.alloc-faculty-cb:checked');
  const faculty_ids = Array.from(checkboxes).map(cb => parseInt(cb.value));

  try {
    const res = await fetch('/api/admin/subjects/allocate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject_id: subjectId, faculty_ids })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Failed to update allocations', 'error');
      return;
    }

    showToast('Faculty allocations updated successfully!', 'success');
    closeAllocateModal();
    loadAdminSubjects();
  } catch (err) {
    showToast('Network error while saving allocations', 'error');
  }
}
