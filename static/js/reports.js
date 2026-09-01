// ====================================================================
// EduAttend Pro - Dynamic Attendance Matrix Reports & Export Engine
// ====================================================================

let activeReportPreset = 'session';
let currentReportData = null;

// Initialize Reports View
function initReportsView() {
  const yearSelect = document.getElementById('reportYearSelect');
  if (currentUser.role === 'faculty') {
    yearSelect.value = currentUser.assigned_year;
    yearSelect.disabled = true; // Faculty locked to their assigned year
  } else {
    yearSelect.disabled = false;
  }

  // Set default dates for custom inputs
  const today = new Date();
  document.getElementById('reportStartDate').value = '2026-08-31';
  document.getElementById('reportEndDate').value = formatDateISO(today);

  setReportPreset('session');
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
    startBox.style.display = 'none';
    endBox.style.display = 'none';
  } else if (preset === '15') {
    const btn = document.getElementById('btnPreset15');
    if (btn) btn.classList.add('active');
    startBox.style.display = 'none';
    endBox.style.display = 'none';
  } else if (preset === '30') {
    const btn = document.getElementById('btnPreset30');
    if (btn) btn.classList.add('active');
    startBox.style.display = 'none';
    endBox.style.display = 'none';
  } else if (preset === 'custom') {
    const btn = document.getElementById('btnPresetCustom');
    if (btn) btn.classList.add('active');
    startBox.style.display = 'block';
    endBox.style.display = 'block';
  }

  fetchReportData();
}

async function fetchReportData() {
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

  const thead = document.getElementById('reportMatrixHeader');
  const tbody = document.getElementById('reportMatrixBody');
  tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px;">Calculating attendance matrix (excluding Saturdays, Sundays & Holidays)...</td></tr>`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    currentReportData = data;
    renderMatrixTable(data);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 32px; color: var(--danger);">Failed to load report data.</td></tr>`;
  }
}

function renderMatrixTable(data) {
  const thead = document.getElementById('reportMatrixHeader');
  const tbody = document.getElementById('reportMatrixBody');

  // Update banner meta
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

  // 1. Build Header Row
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

  // 2. Build Student Rows
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

    // Determine percentage styling
    let pctClass = 'pct-high';
    if (s.percentage < 60) pctClass = 'pct-low';
    else if (s.percentage < 75) pctClass = 'pct-mid';

    rowHtml += `
        <td style="font-weight: 700; color: #047857;">${s.present_count}</td>
        <td style="font-weight: 700; color: #b91c1c;">${s.absent_count}</td>
        <td>
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
