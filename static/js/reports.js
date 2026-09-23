// ====================================================================
// EduAttend Pro - Dynamic Attendance Matrix Reports & Export Engine
// ====================================================================

let activeReportType = 'subject'; // 'subject' or 'class'
let activeReportPreset = 'session';
let currentReportData = null;
let allocatedSubjectsForReport = [];

// Initialize Reports View
async function initReportsView() {
  const btnSubject = document.getElementById('btnReportTypeSubject');
  const btnClass = document.getElementById('btnReportTypeClass');

  // Role permissions on report types
  if (currentUser.role === 'faculty') {
    if (currentUser.is_coordinator) {
      // Coordinator can view both Subject Reports and their Coordinated Class Matrix
      if (btnSubject) btnSubject.style.display = 'inline-flex';
      if (btnClass) btnClass.style.display = 'inline-flex';
      activeReportType = 'subject'; // Default to Subject
    } else {
      // Regular Faculty ONLY sees Subject-Wise Reports for their allocated subjects
      if (btnSubject) btnSubject.style.display = 'inline-flex';
      if (btnClass) btnClass.style.display = 'none';
      activeReportType = 'subject';
    }
  } else {
    // Admin has full access to both
    if (btnSubject) btnSubject.style.display = 'inline-flex';
    if (btnClass) btnClass.style.display = 'inline-flex';
    activeReportType = 'class'; // Default to Class Matrix for admin
  }

  // Populate Class Select for Coordinator / Admin
  const yearSelect = document.getElementById('reportYearSelect');
  if (yearSelect) {
    if (currentUser.role === 'faculty' && currentUser.is_coordinator && currentUser.coordinated_classes) {
      const allowed = currentUser.coordinated_classes;
      yearSelect.innerHTML = allowed.map(c => `<option value="${c}">${c}</option>`).join('');
      yearSelect.value = allowed[0];
    } else {
      const allClasses = ['2nd Year (CSE)', '2nd Year (AI-DS)', '3rd Year (CSE)', '3rd Year (AI-DS)', '4th Year (CSE)', '4th Year (AI-DS)'];
      yearSelect.innerHTML = allClasses.map(c => `<option value="${c}">${c}</option>`).join('');
    }
  }

  // Load Allocated Subjects into dropdown
  await loadSubjectsForReportDropdown();

  // Set default dates for custom inputs
  const today = new Date();
  document.getElementById('reportStartDate').value = '2026-08-31';
  document.getElementById('reportEndDate').value = formatDateISO(today);

  setReportType(activeReportType);
}

async function loadSubjectsForReportDropdown() {
  const subjSelect = document.getElementById('reportSubjectSelect');
  if (!subjSelect) return;

  try {
    const res = await fetch('/api/faculty/my-subjects');
    const data = await res.json();
    allocatedSubjectsForReport = data.subjects || [];

    if (allocatedSubjectsForReport.length === 0) {
      subjSelect.innerHTML = '<option value="">No allocated subjects found</option>';
    } else {
      subjSelect.innerHTML = allocatedSubjectsForReport.map(s => `
        <option value="${s.id}">${s.code} - ${s.name} (${s.type} • ${s.year})</option>
      `).join('');
    }
  } catch (err) {
    subjSelect.innerHTML = '<option value="">Failed to load subjects</option>';
  }
}

function setReportType(type) {
  activeReportType = type;
  const btnSubject = document.getElementById('btnReportTypeSubject');
  const btnClass = document.getElementById('btnReportTypeClass');
  const subjBox = document.getElementById('reportSubjectBox');
  const classBox = document.getElementById('reportClassBox');
  const presetBox = document.getElementById('reportPresetBox');
  const startBox = document.getElementById('customDateRangeBox');
  const endBox = document.getElementById('customDateRangeEndBox');

  if (type === 'subject') {
    if (btnSubject) { btnSubject.className = 'btn btn-sm btn-primary'; }
    if (btnClass) { btnClass.className = 'btn btn-sm btn-outline'; }
    if (subjBox) subjBox.style.display = 'block';
    if (classBox) classBox.style.display = 'none';
    if (presetBox) presetBox.style.display = 'none';
    if (startBox) startBox.style.display = 'none';
    if (endBox) endBox.style.display = 'none';
  } else {
    if (btnSubject) { btnSubject.className = 'btn btn-sm btn-outline'; }
    if (btnClass) { btnClass.className = 'btn btn-sm btn-primary'; }
    if (subjBox) subjBox.style.display = 'none';
    if (classBox) classBox.style.display = 'block';
    if (presetBox) presetBox.style.display = 'block';
    setReportPreset(activeReportPreset);
  }

  fetchReportData();
}

function formatDateISO(d) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function setReportPreset(preset) {
  activeReportPreset = preset;
  document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));

  const startBox = document.getElementById('customDateRangeBox');
  const endBox = document.getElementById('customDateRangeEndBox');

  if (preset === 'session') {
    const btn = document.getElementById('btnPresetSession');
    if (btn) btn.classList.add('active');
    if (startBox) startBox.style.display = 'none';
    if (endBox) endBox.style.display = 'none';
  } else if (preset === '15') {
    const btn = document.getElementById('btnPreset15');
    if (btn) btn.classList.add('active');
    if (startBox) startBox.style.display = 'none';
    if (endBox) endBox.style.display = 'none';
  } else if (preset === '30') {
    const btn = document.getElementById('btnPreset30');
    if (btn) btn.classList.add('active');
    if (startBox) startBox.style.display = 'none';
    if (endBox) endBox.style.display = 'none';
  } else if (preset === 'custom') {
    const btn = document.getElementById('btnPresetCustom');
    if (btn) btn.classList.add('active');
    if (startBox) startBox.style.display = 'block';
    if (endBox) endBox.style.display = 'block';
  }

  if (activeReportType === 'class') {
    fetchReportData();
  }
}

async function fetchReportData() {
  const thead = document.getElementById('reportMatrixHeader');
  const tbody = document.getElementById('reportMatrixBody');

  if (activeReportType === 'subject') {
    const subjSelect = document.getElementById('reportSubjectSelect');
    const subjectId = subjSelect ? subjSelect.value : null;

    if (!subjectId) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px; color: var(--slate-500);">No subject selected. Please select an allocated subject.</td></tr>`;
      return;
    }

    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px;">Loading subject lecture matrix & records...</td></tr>`;

    try {
      const res = await fetch(`/api/reports/subject-attendance?subject_id=${subjectId}`);
      const data = await res.json();
      if (!res.ok) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px; color: var(--danger);">${data.error || 'Failed to load report'}</td></tr>`;
        return;
      }
      currentReportData = data;
      renderSubjectMatrixTable(data);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px; color: var(--danger);">Failed to load subject report data.</td></tr>`;
    }
  } else {
    // Class Daily Attendance Matrix
    const year = document.getElementById('reportYearSelect').value;
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;

    let url = `/api/reports/attendance?year=${encodeURIComponent(year)}&preset=${activeReportPreset}`;
    if (activeReportPreset === 'custom') {
      if (!startDate || !endDate) {
        showToast('Please select both start and end dates', 'warning');
        return;
      }
      url += `&start_date=${startDate}&end_date=${endDate}`;
    }

    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px;">Calculating daily class matrix (excluding Saturdays, Sundays & Holidays)...</td></tr>`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      currentReportData = data;
      renderClassMatrixTable(data);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px; color: var(--danger);">Failed to load report data.</td></tr>`;
    }
  }
}

// 1. Render Subject-Wise Attendance Matrix
function renderSubjectMatrixTable(data) {
  const thead = document.getElementById('reportMatrixHeader');
  const tbody = document.getElementById('reportMatrixBody');
  const subj = data.subject || {};

  // Update banner meta
  document.getElementById('reportHeaderMeta').textContent = 
    `Subject: ${subj.code} - ${subj.name} (${subj.type}) | Class: ${subj.year} (${subj.department} Sem ${subj.semester}) | Conducted by: ${currentUser.name || 'Faculty'}`;
  document.getElementById('reportTotalWorkingDays').textContent = `${data.total_lectures || 0} Lectures`;
  document.getElementById('reportClassAvgPct').textContent = `${data.summary.subject_average_percentage}%`;

  const sessions = data.sessions || [];
  const students = data.students_report || [];

  if (students.length === 0) {
    thead.innerHTML = '';
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 32px; color: var(--slate-500);">No active students found in ${subj.year}.</td></tr>`;
    return;
  }

  // Header Row
  let headerHtml = `
    <tr>
      <th class="col-roll" style="width: 50px;">Roll</th>
      <th class="col-student">Student Name</th>
      <th style="min-width: 100px;">Enrollment</th>
  `;

  if (sessions.length === 0) {
    headerHtml += `<th style="padding: 12px; color: var(--slate-500);">No lectures taken yet</th>`;
  } else {
    sessions.forEach(sess => {
      const dParts = sess.date.split('-');
      const dStr = `${dParts[2]}/${dParts[1]}`;
      const slotShort = (sess.slot || 'Lec').replace('Lecture ', 'L').replace('Lab Session ', 'Lab');
      headerHtml += `
        <th style="min-width: 60px; font-size: 11px; padding: 6px 4px; text-align: center;" title="${sess.date} - ${sess.slot} (${sess.topic || 'No topic'})">
          <strong>${dStr}</strong><br>
          <span style="font-size: 10px; opacity: 0.85;">${slotShort}</span>
        </th>
      `;
    });
  }

  headerHtml += `
      <th style="min-width: 60px; background: #ecfdf5; color: #047857;">Present</th>
      <th style="min-width: 60px; background: #fef2f2; color: #b91c1c;">Absent</th>
      <th style="min-width: 85px; background: #f0f9ff; color: #0369a1;">Subject %</th>
    </tr>
  `;
  thead.innerHTML = headerHtml;

  // Student Rows
  let bodyHtml = students.map(s => {
    let rowHtml = `
      <tr>
        <td class="col-roll"><strong>${s.roll_no}</strong></td>
        <td class="col-student">
          <div style="font-weight: 600; color: var(--slate-900);">${s.name}</div>
        </td>
        <td style="font-size: 12px; color: var(--slate-600);">${s.enrollment_no}</td>
    `;

    if (sessions.length === 0) {
      rowHtml += `<td style="color: var(--slate-400); text-align: center;">-</td>`;
    } else {
      sessions.forEach(sess => {
        const status = s.lectures[String(sess.id)] || '-';
        let badgeClass = 'badge-att-na';
        let shortChar = '-';

        if (status === 'Present') {
          badgeClass = 'badge-att-p';
          shortChar = 'P';
        } else if (status === 'Absent') {
          badgeClass = 'badge-att-a';
          shortChar = 'A';
        }

        rowHtml += `<td style="text-align: center;"><span class="${badgeClass}">${shortChar}</span></td>`;
      });
    }

    let pctClass = 'pct-high';
    if (s.percentage < 60) pctClass = 'pct-low';
    else if (s.percentage < 75) pctClass = 'pct-mid';

    rowHtml += `
        <td style="font-weight: 700; color: #047857; text-align: center;">${s.present_count}</td>
        <td style="font-weight: 700; color: #b91c1c; text-align: center;">${s.absent_count}</td>
        <td style="text-align: center;">
          <span class="pct-badge ${pctClass}">${s.percentage}%</span>
        </td>
      </tr>
    `;
    return rowHtml;
  }).join('');

  tbody.innerHTML = bodyHtml;
}

// 2. Render Daily Class Attendance Matrix
function renderClassMatrixTable(data) {
  const thead = document.getElementById('reportMatrixHeader');
  const tbody = document.getElementById('reportMatrixBody');

  document.getElementById('reportHeaderMeta').textContent = 
    `Class: ${data.year} | Range: ${formatDisplayDate(data.start_date)} to ${formatDisplayDate(data.end_date)} (Excludes all Saturdays, Sundays & Holidays)`;
  document.getElementById('reportTotalWorkingDays').textContent = data.summary.total_working_days;
  document.getElementById('reportClassAvgPct').textContent = `${data.summary.class_average_percentage}%`;

  const workingDates = data.working_dates || [];
  const students = data.students_report || [];

  if (students.length === 0) {
    thead.innerHTML = '';
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 32px; color: var(--slate-500);">No student records found for this period.</td></tr>`;
    return;
  }

  // Header Row
  let headerHtml = `
    <tr>
      <th class="col-roll" style="width: 50px;">Roll</th>
      <th class="col-student">Student Name</th>
  `;

  workingDates.forEach(d => {
    headerHtml += `<th style="min-width: 54px; font-size: 11px;">${formatShortDate(d)}</th>`;
  });

  headerHtml += `
      <th style="min-width: 60px; background: #ecfdf5; color: #047857;">Present</th>
      <th style="min-width: 60px; background: #fef2f2; color: #b91c1c;">Absent</th>
      <th style="min-width: 85px; background: #f0f9ff; color: #0369a1;">Attendance %</th>
    </tr>
  `;
  thead.innerHTML = headerHtml;

  // Student Rows
  let bodyHtml = students.map(s => {
    let rowHtml = `
      <tr>
        <td class="col-roll"><strong>${s.roll_no}</strong></td>
        <td class="col-student">
          <div style="font-weight: 600; color: var(--slate-900);">${s.name}</div>
        </td>
    `;

    workingDates.forEach(d => {
      const status = s.dates[d] || '-';
      let badgeClass = 'badge-att-na';
      let shortChar = '-';

      if (status === 'Present') {
        badgeClass = 'badge-att-p';
        shortChar = 'P';
      } else if (status === 'Absent') {
        badgeClass = 'badge-att-a';
        shortChar = 'A';
      }

      rowHtml += `<td><span class="${badgeClass}">${shortChar}</span></td>`;
    });

    let pctClass = 'pct-high';
    if (s.percentage < 60) pctClass = 'pct-low';
    else if (s.percentage < 75) pctClass = 'pct-mid';

    rowHtml += `
        <td style="font-weight: 700; color: #047857; text-align: center;">${s.present_count}</td>
        <td style="font-weight: 700; color: #b91c1c; text-align: center;">${s.absent_count}</td>
        <td style="text-align: center;">
          <span class="pct-badge ${pctClass}">${s.percentage}%</span>
        </td>
      </tr>
    `;
    return rowHtml;
  }).join('');

  tbody.innerHTML = bodyHtml;
}

function formatShortDate(dateStr) {
  try {
    const parts = dateStr.split('-');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = parts[2];
    const month = months[parseInt(parts[1]) - 1];
    return `${day}<br>${month}`;
  } catch (e) {
    return dateStr;
  }
}

function formatDisplayDate(dateStr) {
  try {
    const parts = dateStr.split('-');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${parts[2]} ${months[parseInt(parts[1]) - 1]} ${parts[0]}`;
  } catch (e) {
    return dateStr;
  }
}

// Export to Excel via Server-Side endpoint
function exportToExcel() {
  const year = document.getElementById('reportYearSelect').value;
  const startDate = document.getElementById('reportStartDate').value;
  const endDate = document.getElementById('reportEndDate').value;

  let url = `/api/reports/export/excel?year=${encodeURIComponent(year)}&preset=${activeReportPreset}`;
  if (activeReportPreset === 'custom') {
    url += `&start_date=${startDate}&end_date=${endDate}`;
  }

  showToast('Preparing formatted Excel workbook...', 'info');
  window.location.href = url;
}

// Export to PDF via html2pdf
function exportToPDF() {
  const element = document.getElementById('printableReportArea');
  const year = document.getElementById('reportYearSelect').value;

  showToast('Generating high-resolution PDF...', 'info');

  const opt = {
    margin: [10, 10, 10, 10],
    filename: `Attendance_Report_${year.replace(' ', '_')}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
  };

  html2pdf().set(opt).from(element).save().then(() => {
    showToast('PDF downloaded successfully!', 'success');
  }).catch(err => {
    showToast('Printing report layout instead...', 'info');
    window.print();
  });
}

// Print Directly
function printReport() {
  window.print();
}
