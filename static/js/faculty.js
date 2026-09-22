// ====================================================================
// EduAttend Pro - Fast Mobile-First Faculty Attendance Module
// ====================================================================

let facultyStudents = [];
let attendanceState = {}; // { student_id: 'Present' | 'Absent' }
let isDateBlocked = false;
let isAlreadySubmitted = false;

function getCurrentSelectedFacultyClass() {
  const select = document.getElementById('facultyClassSelect');
  if (select && select.value) {
    return select.value;
  }
  return currentUser?.assigned_year || '3rd Year (CSE)';
}

// Initialize Faculty Mark Attendance View
async function initFacultyMarkAttendance() {
  const classSelect = document.getElementById('facultyClassSelect');
  const assignedYear = currentUser.assigned_year || '3rd Year (CSE)';
  
  if (classSelect) {
    // Select faculty's assigned class by default
    const matchingOption = Array.from(classSelect.options).find(o => o.value === assignedYear || o.value.includes(assignedYear));
    if (matchingOption) {
      classSelect.value = matchingOption.value;
    }
  }

  const selectedYear = getCurrentSelectedFacultyClass();
  const yearHeader = document.getElementById('facultyYearHeader');
  if (yearHeader) yearHeader.textContent = `${selectedYear} Daily Attendance`;

  // Set default date to today (YYYY-MM-DD)
  const dateInput = document.getElementById('attendanceDateInput');
  if (!dateInput.value) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    dateInput.value = `${yyyy}-${mm}-${dd}`;
  }

  // Load students for this class
  await loadFacultyStudents();
  // Check date status (Sunday / Holiday / Already submitted)
  await onAttendanceDateChange();
}

async function onFacultyClassChange() {
  const selectedYear = getCurrentSelectedFacultyClass();
  const yearHeader = document.getElementById('facultyYearHeader');
  if (yearHeader) yearHeader.textContent = `${selectedYear} Daily Attendance`;
  await loadFacultyStudents();
  await onAttendanceDateChange();
}

// Fetch Active Students for Faculty's Year
async function loadFacultyStudents() {
  try {
    const year = getCurrentSelectedFacultyClass();
    const res = await fetch(`/api/faculty/students?year=${encodeURIComponent(year)}`);
    const data = await res.json();
    facultyStudents = data.students || [];
    
    // Initialize default attendance state: all Present for rapid submission
    attendanceState = {};
    facultyStudents.forEach(s => {
      attendanceState[s.id] = 'Present';
    });
    renderStudentsList();
  } catch (err) {
    showToast('Failed to load students list', 'error');
  }
}

// Triggered when date selector changes
async function onAttendanceDateChange() {
  const dateInput = document.getElementById('attendanceDateInput');
  const dateStr = dateInput.value;
  const year = getCurrentSelectedFacultyClass();
  const alertBox = document.getElementById('dateAlertBox');
  const submitBtn = document.getElementById('btnSubmitAttendance');
  const batchBtns = document.getElementById('batchActionButtons');
  const summaryText = document.getElementById('submitSummaryText');

  alertBox.style.display = 'none';
  alertBox.className = 'alert-box';
  isDateBlocked = false;
  isAlreadySubmitted = false;

  try {
    const res = await fetch(`/api/attendance/check-date?year=${encodeURIComponent(year)}&date=${dateStr}`);
    const data = await res.json();

    // 0. Pre-session check
    if (data.is_pre_session) {
      isDateBlocked = true;
      alertBox.className = 'alert-box alert-warning';
      alertBox.innerHTML = `
        <i data-lucide="calendar-off" style="width: 20px; height: 20px;"></i>
        <span><strong>Pre-Session Date:</strong> Academic session officially started on <strong>31 Aug 2026</strong>. Attendance cannot be recorded for prior dates.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = 'Session started on 31 Aug 2026.';
    }
    // 1. Weekend check (Saturday & Sunday)
    else if (data.is_weekend || data.is_sunday) {
      isDateBlocked = true;
      const dayTitle = data.weekend_name ? `${data.weekend_name} (College Weekend Holiday)` : 'Weekend (Saturday/Sunday)';
      alertBox.className = 'alert-box alert-warning';
      alertBox.innerHTML = `
        <i data-lucide="alert-triangle" style="width: 20px; height: 20px;"></i>
        <span><strong>${dayTitle}:</strong> College is closed on Saturdays and Sundays. Attendance cannot be submitted.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = 'Saturdays & Sundays are scheduled college holidays.';
    }
    // 2. Holiday check
    else if (data.is_holiday) {
      isDateBlocked = true;
      alertBox.className = 'alert-box alert-warning';
      alertBox.innerHTML = `
        <i data-lucide="calendar-off" style="width: 20px; height: 20px;"></i>
        <span><strong>Holiday:</strong> ${data.holiday_reason}. Attendance is not recorded on declared holidays.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = 'Declared College Holiday.';
    }
    // 3. Already Submitted check
    else if (data.is_submitted) {
      isAlreadySubmitted = true;
      alertBox.className = 'alert-box alert-info';
      const subTime = data.submission_info.submitted_at || '';
      const facultyName = data.submission_info.faculty_name || 'Faculty';
      alertBox.innerHTML = `
        <i data-lucide="check-circle-2" style="width: 20px; height: 20px;"></i>
        <span><strong>Attendance Already Submitted:</strong> Recorded on ${subTime} by ${facultyName}. Read-only mode.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = `Attendance finalized for ${dateStr}.`;

      // Map existing records
      if (data.records && data.records.length > 0) {
        data.records.forEach(r => {
          attendanceState[r.student_id] = r.status;
        });
      }
    }
    // 4. Clean working day - Ready to take attendance
    else {
      submitBtn.disabled = false;
      batchBtns.style.display = 'flex';
      summaryText.textContent = `Marking attendance for ${facultyStudents.length} active students.`;
    }

    renderAttendanceStudentList();
    updateAttendanceCounters();
    lucide.createIcons({ root: alertBox });
  } catch (err) {
    showToast('Failed to verify date status', 'error');
  }
}

// Render student list with interactive touch buttons
function renderAttendanceStudentList() {
  const tbody = document.getElementById('attendanceTableBody');
  if (facultyStudents.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 32px; color: var(--slate-500);">No active students found for this year.</td></tr>`;
    return;
  }

  tbody.innerHTML = facultyStudents.map(student => {
    const currentStatus = attendanceState[student.id] || 'Present';
    const isPresentActive = currentStatus === 'Present';
    const isAbsentActive = currentStatus === 'Absent';
    const disabledAttr = (isDateBlocked || isAlreadySubmitted) ? 'disabled' : '';

    return `
      <tr id="student-row-${student.id}">
        <td><strong style="font-size: 14px;">${student.roll_no}</strong></td>
        <td>
          <div style="font-weight: 600; color: var(--slate-900);">${student.name}</div>
          <div style="font-size: 11px; color: var(--slate-500);" class="show-mobile">${student.enrollment_no || ''}</div>
        </td>
        <td class="hide-mobile" style="color: var(--slate-600);">${student.enrollment_no || '-'}</td>
        <td>
          <div class="attendance-toggle-group">
            <button type="button" class="btn-toggle-att btn-present ${isPresentActive ? 'active' : ''}" 
              onclick="setStudentAttendance(${student.id}, 'Present')" ${disabledAttr}>
              P (Present)
            </button>
            <button type="button" class="btn-toggle-att btn-absent ${isAbsentActive ? 'active' : ''}" 
              onclick="setStudentAttendance(${student.id}, 'Absent')" ${disabledAttr}>
              A (Absent)
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Set Individual Student Attendance
function setStudentAttendance(studentId, status) {
  if (isDateBlocked || isAlreadySubmitted) return;

  attendanceState[studentId] = status;
  
  // Fast DOM update for instant UI feedback without full re-render
  const row = document.getElementById(`student-row-${studentId}`);
  if (row) {
    const btnP = row.querySelector('.btn-present');
    const btnA = row.querySelector('.btn-absent');
    if (status === 'Present') {
      btnP.classList.add('active');
      btnA.classList.remove('active');
    } else {
      btnP.classList.remove('active');
      btnA.classList.add('active');
    }
  }

  updateAttendanceCounters();
}

// Batch Actions: Mark All Present / Mark All Absent
function markAll(status) {
  if (isDateBlocked || isAlreadySubmitted) return;

  facultyStudents.forEach(s => {
    attendanceState[s.id] = status;
  });

  renderAttendanceStudentList();
  updateAttendanceCounters();
  showToast(`All students marked as ${status}`, 'info');
}

// Update Present / Absent counter pills
function updateAttendanceCounters() {
  const total = facultyStudents.length;
  let present = 0;
  let absent = 0;

  facultyStudents.forEach(s => {
    const st = attendanceState[s.id];
    if (st === 'Present') present++;
    else if (st === 'Absent') absent++;
  });

  document.getElementById('totalStudentCount').textContent = total;
  document.getElementById('presentCount').textContent = present;
  document.getElementById('absentCount').textContent = absent;
}

// Submit Attendance to Backend
async function submitAttendanceData() {
  if (isDateBlocked) {
    showToast('Cannot submit attendance on Saturday, Sunday or College Holiday.', 'error');
    return;
  }
  if (isAlreadySubmitted) {
    showToast('Attendance already submitted for this date.', 'warning');
    return;
  }

  const dateStr = document.getElementById('attendanceDateInput').value;
  const year = getCurrentSelectedFacultyClass();
  const submitBtn = document.getElementById('btnSubmitAttendance');

  const records = facultyStudents.map(s => ({
    student_id: s.id,
    status: attendanceState[s.id] || 'Present'
  }));

  if (records.length === 0) {
    showToast('No students to submit attendance for.', 'warning');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span>Saving Attendance...</span>';

  try {
    const res = await fetch('/api/attendance/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        year: year,
        date: dateStr,
        records: records
      })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Submission failed.', 'error');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i data-lucide="check"></i><span>Submit Attendance</span>';
      lucide.createIcons();
      return;
    }

    showToast('Attendance submitted successfully!', 'success');
    await onAttendanceDateChange(); // Refresh state to show submitted status
  } catch (err) {
    showToast('Network error while submitting attendance', 'error');
  } finally {
    submitBtn.disabled = isAlreadySubmitted || isDateBlocked;
    submitBtn.innerHTML = '<i data-lucide="check"></i><span>Submit Attendance</span>';
    lucide.createIcons();
  }
}

// Load Faculty Submission History
async function loadFacultyHistory() {
  const tbody = document.getElementById('facultyHistoryTableBody');
  const year = currentUser.assigned_year || '2nd Year';
  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px;">Loading submission logs...</td></tr>`;

  try {
    const res = await fetch('/api/admin/dashboard');
    const data = await res.json();
    
    // Filter recent submissions for this faculty's year
    const mySubmissions = (data.recent_submissions || []).filter(s => s.year === year);

    if (mySubmissions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 32px; color: var(--slate-500);">No attendance records found for ${year}.</td></tr>`;
      return;
    }

    tbody.innerHTML = mySubmissions.map(item => `
      <tr>
        <td><strong>${item.date}</strong></td>
        <td><span class="badge badge-indigo">${item.year}</span></td>
        <td>${item.submitted_at || '-'}</td>
        <td><span class="status-badge status-submitted">${item.present_count || 0} Present</span></td>
        <td><span class="status-badge status-pending">${item.absent_count || 0} Absent</span></td>
        <td><strong>${item.student_count || 0} Students</strong></td>
        <td>
          <button class="btn btn-outline btn-xs" onclick="viewHistoryDate('${item.date}')">
            <i data-lucide="eye"></i> View
          </button>
        </td>
      </tr>
    `).join('');
    lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger);">Failed to load history.</td></tr>`;
  }
}

function viewHistoryDate(dateStr) {
  document.getElementById('attendanceDateInput').value = dateStr;
  switchView('faculty-mark');
}

// ====================================================================
// Subject-Wise Attendance Engine
// ====================================================================

let mySubjects = [];
let activeSubject = null;
let subjStudents = [];
let subjAttendanceState = {};
let isSubjDateBlocked = false;
let isSubjAlreadySubmitted = false;

async function initFacultySubjectsView() {
  const welcomeTitle = document.getElementById('facultyWelcomeTitle');
  if (welcomeTitle) {
    welcomeTitle.textContent = `${currentUser.name || 'Faculty'} - Allocated Subjects`;
  }
  await loadFacultyMySubjects();
  await loadSubjectHistory();
}

async function loadFacultyMySubjects() {
  const grid = document.getElementById('mySubjectsGrid');
  grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--slate-500);"><i data-lucide="loader" class="spin"></i> Loading allocated subjects...</div>`;
  lucide.createIcons();

  try {
    const res = await fetch('/api/faculty/my-subjects');
    const data = await res.json();
    mySubjects = data.subjects || [];

    if (mySubjects.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 48px 24px; background: white; border-radius: 12px; border: 1px dashed var(--border-color);">
          <i data-lucide="book-x" style="width: 48px; height: 48px; color: var(--slate-400); margin-bottom: 12px;"></i>
          <h3 style="font-size: 1.1rem; color: var(--slate-700); font-weight: 600;">No Subjects Allocated Yet</h3>
          <p style="color: var(--slate-500); font-size: 14px; margin-top: 4px;">Please ask Administrator to allocate subjects from the Timetable to your profile.</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    grid.innerHTML = mySubjects.map(s => {
      const isLab = s.type === 'Practical';
      const typeBadgeClass = isLab ? 'badge-purple' : 'badge-indigo';
      const typeIcon = isLab ? 'flask-conical' : 'book-open';
      const deptBadgeClass = s.department === 'AI-DS' ? 'badge-amber' : 'badge-sky';

      return `
        <div class="subject-card">
          <div class="subject-card-header">
            <div>
              <div class="subject-code">${s.code}</div>
              <h3 class="subject-name">${s.name}</h3>
            </div>
            <span class="badge ${typeBadgeClass}">
              <i data-lucide="${typeIcon}" style="width: 12px; height: 12px; margin-right: 4px;"></i> ${s.type}
            </span>
          </div>

          <div class="subject-meta-tags">
            <span class="badge ${deptBadgeClass}">${s.department} (Sem ${s.semester})</span>
            <span class="badge badge-slate">${s.year}</span>
            <span class="badge badge-slate"><i data-lucide="users" style="width: 12px; height: 12px; margin-right: 3px;"></i> ${s.student_count || 0} Students</span>
          </div>

          <div class="subject-card-actions">
            <button class="btn btn-primary btn-block" onclick="openSubjectAttendance(${s.id})">
              <i data-lucide="check-square"></i>
              <span>Take Attendance</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--danger); padding: 30px;">Failed to load subjects. Please check connection.</div>`;
  }
}

async function openSubjectAttendance(subjectId) {
  activeSubject = mySubjects.find(s => s.id === subjectId);
  if (!activeSubject) {
    try {
      const res = await fetch(`/api/faculty/subject-students?subject_id=${subjectId}`);
      const data = await res.json();
      activeSubject = data.subject;
    } catch (e) {}
  }

  if (!activeSubject) return;

  // Setup banner headers
  document.getElementById('activeSubjTitle').textContent = `${activeSubject.code}: ${activeSubject.name}`;
  document.getElementById('activeSubjType').textContent = activeSubject.type;
  document.getElementById('activeSubjType').className = `badge ${activeSubject.type === 'Practical' ? 'badge-purple' : 'badge-indigo'}`;
  document.getElementById('activeSubjYear').textContent = activeSubject.year;
  document.getElementById('activeSubjDept').textContent = `${activeSubject.department} (Sem ${activeSubject.semester})`;
  document.getElementById('activeSubjStudents').textContent = `${activeSubject.student_count || 0} Active Students`;

  // Set default date to today
  const dateInput = document.getElementById('subjAttDateInput');
  if (!dateInput.value) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    dateInput.value = `${yyyy}-${mm}-${dd}`;
  }

  // Set default slot based on type
  const slotSelect = document.getElementById('subjAttSlotSelect');
  if (activeSubject.type === 'Practical') {
    slotSelect.value = 'Lab Session (B1)';
  } else {
    slotSelect.value = 'Lecture 1 (10:00 - 11:00 AM)';
  }

  // Switch UI panels
  document.getElementById('subjectsGridView').style.display = 'none';
  document.getElementById('subjectAttendancePanel').style.display = 'block';

  // Load students and check date
  await loadSubjectStudents(subjectId);
  await onSubjectDateOrSlotChange();

  lucide.createIcons();
  document.getElementById('subjectAttendancePanel').scrollIntoView({ behavior: 'smooth' });
}

function closeSubjectAttendancePanel() {
  document.getElementById('subjectAttendancePanel').style.display = 'none';
  document.getElementById('subjectsGridView').style.display = 'block';
  loadSubjectHistory();
}

async function loadSubjectStudents(subjectId) {
  try {
    const res = await fetch(`/api/faculty/subject-students?subject_id=${subjectId}`);
    const data = await res.json();
    subjStudents = data.students || [];

    subjAttendanceState = {};
    subjStudents.forEach(s => {
      subjAttendanceState[s.id] = 'Present';
    });

    renderSubjAttendanceStudentList();
  } catch (err) {
    showToast('Failed to load students for this subject', 'error');
  }
}

async function onSubjectDateOrSlotChange() {
  if (!activeSubject) return;

  const dateInput = document.getElementById('subjAttDateInput');
  const slotSelect = document.getElementById('subjAttSlotSelect');
  const dateStr = dateInput.value;
  const slot = slotSelect.value;

  const alertBox = document.getElementById('subjDateAlertBox');
  const submitBtn = document.getElementById('btnSubmitSubjAttendance');
  const batchBtns = document.getElementById('subjBatchActionButtons');
  const summaryText = document.getElementById('subjSubmitSummaryText');

  alertBox.style.display = 'none';
  alertBox.className = 'alert-box';
  isSubjDateBlocked = false;
  isSubjAlreadySubmitted = false;

  try {
    const res = await fetch(`/api/faculty/subject-attendance/check?subject_id=${activeSubject.id}&date=${dateStr}&slot=${encodeURIComponent(slot)}`);
    const data = await res.json();

    if (data.is_pre_session) {
      isSubjDateBlocked = true;
      alertBox.className = 'alert-box alert-warning';
      alertBox.innerHTML = `
        <i data-lucide="calendar-off"></i>
        <span><strong>Pre-Session Date:</strong> Session started on <strong>31 Aug 2026</strong>. Attendance cannot be recorded for prior dates.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = 'Session started on 31 Aug 2026.';
    } else if (data.is_weekend) {
      isSubjDateBlocked = true;
      const dayTitle = data.weekend_name ? `${data.weekend_name} (College Weekend Holiday)` : 'Weekend';
      alertBox.className = 'alert-box alert-warning';
      alertBox.innerHTML = `
        <i data-lucide="alert-triangle"></i>
        <span><strong>${dayTitle}:</strong> College is closed on Saturdays and Sundays. Attendance cannot be submitted.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = 'Saturdays & Sundays are college holidays.';
    } else if (data.is_holiday) {
      isSubjDateBlocked = true;
      alertBox.className = 'alert-box alert-warning';
      alertBox.innerHTML = `
        <i data-lucide="calendar-off"></i>
        <span><strong>Holiday:</strong> ${data.holiday_reason}. Attendance is not recorded on declared holidays.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = 'Declared College Holiday.';
    } else if (data.is_submitted) {
      isSubjAlreadySubmitted = true;
      alertBox.className = 'alert-box alert-info';
      const subTime = data.submission_info?.submitted_at || '';
      const facultyName = data.submission_info?.faculty_name || 'Faculty';
      const topic = data.submission_info?.topic ? ` | Topic: "${data.submission_info.topic}"` : '';

      alertBox.innerHTML = `
        <i data-lucide="check-circle-2"></i>
        <span><strong>Attendance Already Finalized:</strong> Recorded on ${subTime} by ${facultyName}${topic}.</span>
      `;
      alertBox.style.display = 'flex';
      submitBtn.disabled = true;
      batchBtns.style.display = 'none';
      summaryText.textContent = `Attendance already recorded for ${activeSubject.code} (${slot}) on ${dateStr}.`;

      if (data.records && data.records.length > 0) {
        data.records.forEach(r => {
          subjAttendanceState[r.student_id] = r.status;
        });
      }
    } else {
      submitBtn.disabled = false;
      batchBtns.style.display = 'flex';
      summaryText.textContent = `Marking attendance for ${subjStudents.length} students in ${activeSubject.code}.`;
    }

    renderSubjAttendanceStudentList();
    updateSubjAttendanceCounters();
    lucide.createIcons({ root: alertBox });
  } catch (err) {
    showToast('Failed to check subject attendance date', 'error');
  }
}

function renderSubjAttendanceStudentList() {
  const tbody = document.getElementById('subjAttendanceTableBody');
  if (subjStudents.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 32px; color: var(--slate-500);">No active students found for this class.</td></tr>`;
    return;
  }

  tbody.innerHTML = subjStudents.map(student => {
    const currentStatus = subjAttendanceState[student.id] || 'Present';
    const isPresentActive = currentStatus === 'Present';
    const isAbsentActive = currentStatus === 'Absent';
    const disabledAttr = (isSubjDateBlocked || isSubjAlreadySubmitted) ? 'disabled' : '';

    return `
      <tr id="subj-student-row-${student.id}">
        <td><strong style="font-size: 14px;">${student.roll_no}</strong></td>
        <td>
          <div style="font-weight: 600; color: var(--slate-900);">${student.name}</div>
          <div style="font-size: 11px; color: var(--slate-500);" class="show-mobile">${student.enrollment_no || ''}</div>
        </td>
        <td class="hide-mobile" style="color: var(--slate-600);">${student.enrollment_no || '-'}</td>
        <td>
          <div class="attendance-toggle-group">
            <button type="button" class="btn-toggle-att btn-present ${isPresentActive ? 'active' : ''}" 
              onclick="setStudentSubjAttendance(${student.id}, 'Present')" ${disabledAttr}>
              P (Present)
            </button>
            <button type="button" class="btn-toggle-att btn-absent ${isAbsentActive ? 'active' : ''}" 
              onclick="setStudentSubjAttendance(${student.id}, 'Absent')" ${disabledAttr}>
              A (Absent)
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function setStudentSubjAttendance(studentId, status) {
  if (isSubjDateBlocked || isSubjAlreadySubmitted) return;

  subjAttendanceState[studentId] = status;

  const row = document.getElementById(`subj-student-row-${studentId}`);
  if (row) {
    const btnP = row.querySelector('.btn-present');
    const btnA = row.querySelector('.btn-absent');
    if (status === 'Present') {
      btnP.classList.add('active');
      btnA.classList.remove('active');
    } else {
      btnP.classList.remove('active');
      btnA.classList.add('active');
    }
  }

  updateSubjAttendanceCounters();
}

function markAllSubject(status) {
  if (isSubjDateBlocked || isSubjAlreadySubmitted) return;

  subjStudents.forEach(s => {
    subjAttendanceState[s.id] = status;
  });

  renderSubjAttendanceStudentList();
  updateSubjAttendanceCounters();
  showToast(`All students marked as ${status} for ${activeSubject.code}`, 'info');
}

function updateSubjAttendanceCounters() {
  const total = subjStudents.length;
  let present = 0;
  let absent = 0;

  subjStudents.forEach(s => {
    const st = subjAttendanceState[s.id];
    if (st === 'Present') present++;
    else if (st === 'Absent') absent++;
  });

  document.getElementById('subjTotalStudentCount').textContent = total;
  document.getElementById('subjPresentCount').textContent = present;
  document.getElementById('subjAbsentCount').textContent = absent;
}

async function submitSubjAttendanceData() {
  if (!activeSubject) return;

  if (isSubjDateBlocked) {
    showToast('Cannot submit attendance on weekend or college holiday.', 'error');
    return;
  }
  if (isSubjAlreadySubmitted) {
    showToast('Attendance already submitted for this date and slot.', 'warning');
    return;
  }

  const dateStr = document.getElementById('subjAttDateInput').value;
  const slot = document.getElementById('subjAttSlotSelect').value;
  const topic = document.getElementById('subjAttTopicInput').value.trim();
  const submitBtn = document.getElementById('btnSubmitSubjAttendance');

  const records = subjStudents.map(s => ({
    student_id: s.id,
    status: subjAttendanceState[s.id] || 'Present'
  }));

  if (records.length === 0) {
    showToast('No students to submit attendance for.', 'warning');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span>Saving Subject Attendance...</span>';

  try {
    const res = await fetch('/api/faculty/subject-attendance/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject_id: activeSubject.id,
        date: dateStr,
        slot: slot,
        topic: topic,
        records: records
      })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Submission failed.', 'error');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i data-lucide="check"></i><span>Save Subject Attendance</span>';
      lucide.createIcons();
      return;
    }

    showToast(`Attendance saved successfully for ${activeSubject.code}!`, 'success');
    await onSubjectDateOrSlotChange();
    await loadSubjectHistory();
  } catch (err) {
    showToast('Network error while submitting subject attendance', 'error');
  } finally {
    submitBtn.disabled = isSubjAlreadySubmitted || isSubjDateBlocked;
    submitBtn.innerHTML = '<i data-lucide="check"></i><span>Save Subject Attendance</span>';
    lucide.createIcons();
  }
}

async function loadSubjectHistory() {
  const tbody = document.getElementById('subjHistoryTableBody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px;">Loading subject lecture logs...</td></tr>`;

  try {
    const res = await fetch('/api/faculty/subject-attendance/history');
    const data = await res.json();
    const history = data.history || [];

    if (history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--slate-500);">No subject attendance records found yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = history.map(item => {
      const total = item.total_students || 0;
      const pres = item.present_count || 0;
      const pct = total > 0 ? Math.round((pres / total) * 100) : 0;
      const pctBadge = pct >= 75 ? 'status-submitted' : 'status-pending';

      return `
        <tr>
          <td><strong>${item.date}</strong></td>
          <td>
            <div style="font-weight: 600;">${item.subject_code}</div>
            <div style="font-size: 11px; color: var(--slate-500);">${item.subject_name}</div>
          </td>
          <td><span class="badge ${item.subject_type === 'Practical' ? 'badge-purple' : 'badge-indigo'}">${item.subject_type}</span></td>
          <td><span class="badge badge-slate">${item.slot}</span></td>
          <td style="color: var(--slate-700); font-size: 13px;">${item.topic || '<em>General Class</em>'}</td>
          <td><strong>${pres} / ${total}</strong></td>
          <td><span class="status-badge ${pctBadge}">${pct}%</span></td>
        </tr>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger);">Failed to load history.</td></tr>`;
  }
}
