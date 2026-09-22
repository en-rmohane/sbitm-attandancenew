import sqlite3
import os
import io
import csv
from datetime import datetime, timedelta
from functools import wraps
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from flask import Flask, request, jsonify, render_template, send_file, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db_connection, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static',
    template_folder=os.path.join(BASE_DIR, 'templates')
)
app.secret_key = 'super_secret_attendance_system_key_2026'

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)

# Initialize database on start
init_db()

SESSION_START_DATE = '2026-08-31'

# --- Helper Functions ---

def is_weekend(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.weekday() in (5, 6) # Saturday is 5, Sunday is 6 in Python
    except ValueError:
        return False

def get_weekend_name(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if dt.weekday() == 5:
            return 'Saturday'
        elif dt.weekday() == 6:
            return 'Sunday'
        return None
    except ValueError:
        return None

def is_sunday(date_str):
    # Alias for backward compatibility
    return is_weekend(date_str)

def get_holiday_reason(conn, date_str):
    cursor = conn.cursor()
    cursor.execute("SELECT reason FROM holidays WHERE date = ?", (date_str,))
    row = cursor.fetchone()
    return row['reason'] if row else None

def get_working_dates(conn, start_date_str, end_date_str):
    """
    Returns list of working dates (YYYY-MM-DD) excluding Saturdays, Sundays and Holidays.
    Clamped to SESSION_START_DATE (2026-08-31) minimum.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM holidays")
    holiday_set = set(row['date'] for row in cursor.fetchall())

    # Ensure start date is at least SESSION_START_DATE
    if start_date_str < SESSION_START_DATE:
        start_date_str = SESSION_START_DATE

    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    working_dates = []
    curr = start_dt
    while curr <= end_dt:
        d_str = curr.strftime('%Y-%m-%d')
        # Skip Saturday (5), Sunday (6) and college holidays
        if curr.weekday() not in (5, 6) and d_str not in holiday_set:
            working_dates.append(d_str)
        curr += timedelta(days=1)
    return working_dates

# --- Auth Decorators ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# 1. Authentication APIs
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.password_hash, u.role, u.faculty_id,
               f.name as faculty_name, f.assigned_year
        FROM users u
        LEFT JOIN faculty f ON u.faculty_id = f.id
        WHERE u.username = ?
    """, (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['faculty_id'] = user['faculty_id']
    session['assigned_year'] = user['assigned_year']
    session['display_name'] = user['faculty_name'] if user['role'] == 'faculty' else 'Administrator'

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'faculty_id': user['faculty_id'],
            'assigned_year': user['assigned_year'],
            'name': session['display_name']
        }
    })

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 200

    return jsonify({
        'authenticated': True,
        'user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),
            'faculty_id': session.get('faculty_id'),
            'assigned_year': session.get('assigned_year'),
            'name': session.get('display_name')
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

# 2. Faculty & Attendance APIs
@app.route('/api/faculty/students', methods=['GET'])
@login_required
def get_faculty_students():
    year = request.args.get('year')
    # If faculty, force their assigned year
    if session.get('role') == 'faculty':
        year = session.get('assigned_year')

    if not year:
        return jsonify({'error': 'Year parameter is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, roll_no, name, enrollment_no, year, status
        FROM students
        WHERE year = ? AND status = 'active'
        ORDER BY CAST(roll_no AS INTEGER), roll_no ASC
    """, (year,))
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({'year': year, 'students': students})

@app.route('/api/attendance/check-date', methods=['GET'])
@login_required
def check_date():
    year = request.args.get('year')
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    if session.get('role') == 'faculty':
        year = session.get('assigned_year')

    if not year or not date_str:
        return jsonify({'error': 'Year and Date are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # 0. Check Pre-Session Date
    is_pre_session = date_str < SESSION_START_DATE

    # 1. Check Weekend (Saturday or Sunday)
    weekend_name = get_weekend_name(date_str)
    weekend_flag = bool(weekend_name)
    # 2. Check Holiday
    holiday_reason = get_holiday_reason(conn, date_str)
    # 3. Check existing submission
    cursor.execute("""
        SELECT a.id, a.year, a.date, a.submitted_at, f.name as faculty_name
        FROM attendance a
        LEFT JOIN faculty f ON a.faculty_id = f.id
        WHERE a.year = ? AND a.date = ?
    """, (year, date_str))
    existing = cursor.fetchone()

    records = []
    if existing:
        cursor.execute("""
            SELECT ar.student_id, ar.status, s.roll_no, s.name
            FROM attendance_records ar
            JOIN students s ON ar.student_id = s.id
            WHERE ar.attendance_id = ?
            ORDER BY CAST(s.roll_no AS INTEGER), s.roll_no ASC
        """, (existing['id'],))
        records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return jsonify({
        'date': date_str,
        'year': year,
        'is_pre_session': is_pre_session,
        'session_start_date': SESSION_START_DATE,
        'is_sunday': weekend_flag, # Keep for backward compatibility
        'is_weekend': weekend_flag,
        'weekend_name': weekend_name,
        'is_holiday': bool(holiday_reason),
        'holiday_reason': holiday_reason,
        'is_submitted': bool(existing),
        'submission_info': dict(existing) if existing else None,
        'records': records
    })

@app.route('/api/attendance/submit', methods=['POST'])
@login_required
def submit_attendance():
    data = request.get_json() or {}
    year = data.get('year')
    date_str = data.get('date')
    records = data.get('records', []) # [{'student_id': 1, 'status': 'Present'}]

    # Role check: Faculty can only submit for assigned year
    if session.get('role') == 'faculty':
        year = session.get('assigned_year')

    if not year or not date_str or not records:
        return jsonify({'error': 'Year, Date, and student records are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify session start date (31 Aug 2026)
    if date_str < SESSION_START_DATE:
        conn.close()
        return jsonify({'error': f'Cannot submit attendance before session start date ({SESSION_START_DATE}).'}), 400

    # Verify Weekend (Saturday / Sunday)
    if is_weekend(date_str):
        w_name = get_weekend_name(date_str) or 'Weekend'
        conn.close()
        return jsonify({'error': f'Cannot submit attendance on {w_name} (College Holiday / Non-working day).'}), 400

    # Verify Holiday
    h_reason = get_holiday_reason(conn, date_str)
    if h_reason:
        conn.close()
        return jsonify({'error': f'Cannot submit attendance on holiday: {h_reason}'}), 400

    # Check for duplicate
    cursor.execute("SELECT id FROM attendance WHERE year = ? AND date = ?", (year, date_str))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Attendance already submitted for this date.'}), 409

    # Determine faculty_id
    faculty_id = session.get('faculty_id')
    if not faculty_id and session.get('role') == 'admin':
        # Find faculty assigned to this year
        cursor.execute("SELECT id FROM faculty WHERE assigned_year = ?", (year,))
        f_row = cursor.fetchone()
        faculty_id = f_row['id'] if f_row else None

    # Insert Master Record
    submission_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO attendance (year, date, faculty_id, submitted_at, status)
        VALUES (?, ?, ?, ?, 'submitted')
    """, (year, date_str, faculty_id, submission_time))
    attendance_id = cursor.lastrowid

    # Insert individual records
    record_tuples = [
        (attendance_id, r['student_id'], r['status'])
        for r in records
    ]
    cursor.executemany("""
        INSERT INTO attendance_records (attendance_id, student_id, status)
        VALUES (?, ?, ?)
    """, record_tuples)

    conn.commit()
    conn.close()

    return jsonify({
        'message': 'Attendance submitted successfully.',
        'attendance_id': attendance_id,
        'year': year,
        'date': date_str,
        'submission_time': submission_time,
        'total_marked': len(records)
    })

# 2.1 Subject-Wise Attendance APIs
@app.route('/api/faculty/my-subjects', methods=['GET'])
@login_required
def get_faculty_my_subjects():
    faculty_id = session.get('faculty_id')
    role = session.get('role')

    conn = get_db_connection()
    cursor = conn.cursor()

    if role == 'admin' or not faculty_id:
        cursor.execute("""
            SELECT s.id, s.code, s.name, s.type, s.year, s.department, s.semester,
                   GROUP_CONCAT(f.name, ', ') as faculty_names
            FROM subjects s
            LEFT JOIN subject_allocations sa ON s.id = sa.subject_id
            LEFT JOIN faculty f ON sa.faculty_id = f.id
            GROUP BY s.id
            ORDER BY s.department ASC, s.semester ASC, s.code ASC, s.type ASC
        """)
        rows = cursor.fetchall()
        subjects = []
        for r in rows:
            cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE year = ? AND status = 'active'", (r['year'],))
            cnt = cursor.fetchone()['cnt']
            subjects.append({
                'id': r['id'],
                'code': r['code'],
                'name': r['name'],
                'type': r['type'],
                'year': r['year'],
                'department': r['department'],
                'semester': r['semester'],
                'faculty_names': r['faculty_names'] or 'Unallocated',
                'student_count': cnt
            })
    else:
        cursor.execute("""
            SELECT s.id, s.code, s.name, s.type, s.year, s.department, s.semester, sa.role
            FROM subjects s
            JOIN subject_allocations sa ON s.id = sa.subject_id
            WHERE sa.faculty_id = ?
            ORDER BY s.department ASC, s.semester ASC, s.code ASC, s.type ASC
        """, (faculty_id,))
        rows = cursor.fetchall()
        subjects = []
        for r in rows:
            cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE year = ? AND status = 'active'", (r['year'],))
            cnt = cursor.fetchone()['cnt']
            subjects.append({
                'id': r['id'],
                'code': r['code'],
                'name': r['name'],
                'type': r['type'],
                'year': r['year'],
                'department': r['department'],
                'semester': r['semester'],
                'role': r['role'],
                'student_count': cnt
            })

    conn.close()
    return jsonify({'subjects': subjects})

@app.route('/api/faculty/subject-students', methods=['GET'])
@login_required
def get_subject_students():
    subject_id = request.args.get('subject_id')
    if not subject_id:
        return jsonify({'error': 'subject_id parameter is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    subj = cursor.fetchone()
    if not subj:
        conn.close()
        return jsonify({'error': 'Subject not found'}), 404

    cursor.execute("""
        SELECT id, roll_no, name, enrollment_no, year, status
        FROM students
        WHERE year = ? AND status = 'active'
        ORDER BY CAST(roll_no AS INTEGER), roll_no ASC
    """, (subj['year'],))
    students = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({
        'subject': dict(subj),
        'students': students
    })

@app.route('/api/faculty/subject-attendance/check', methods=['GET'])
@login_required
def check_subject_attendance():
    subject_id = request.args.get('subject_id')
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    slot = request.args.get('slot', 'Lecture 1 (10:00 - 11:00 AM)')

    if not subject_id or not date_str:
        return jsonify({'error': 'subject_id and date are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    is_pre_session = date_str < SESSION_START_DATE
    weekend_name = get_weekend_name(date_str)
    holiday_reason = get_holiday_reason(conn, date_str)

    cursor.execute("""
        SELECT sa.id, sa.subject_id, sa.faculty_id, sa.year, sa.date, sa.slot, sa.topic, sa.submitted_at,
               f.name as faculty_name, s.code as subject_code, s.name as subject_name, s.type as subject_type
        FROM subject_attendance sa
        LEFT JOIN faculty f ON sa.faculty_id = f.id
        LEFT JOIN subjects s ON sa.subject_id = s.id
        WHERE sa.subject_id = ? AND sa.date = ? AND sa.slot = ?
    """, (subject_id, date_str, slot))
    existing = cursor.fetchone()

    records = []
    if existing:
        cursor.execute("""
            SELECT sar.student_id, sar.status, st.roll_no, st.name, st.enrollment_no
            FROM subject_attendance_records sar
            JOIN students st ON sar.student_id = st.id
            WHERE sar.subject_attendance_id = ?
            ORDER BY CAST(st.roll_no AS INTEGER), st.roll_no ASC
        """, (existing['id'],))
        records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return jsonify({
        'subject_id': int(subject_id),
        'date': date_str,
        'slot': slot,
        'is_pre_session': is_pre_session,
        'is_weekend': bool(weekend_name),
        'weekend_name': weekend_name,
        'is_holiday': bool(holiday_reason),
        'holiday_reason': holiday_reason,
        'is_submitted': bool(existing),
        'submission_info': dict(existing) if existing else None,
        'records': records
    })

@app.route('/api/faculty/subject-attendance/submit', methods=['POST'])
@login_required
def submit_subject_attendance():
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    date_str = data.get('date')
    slot = data.get('slot', 'Lecture 1 (10:00 - 11:00 AM)')
    topic = data.get('topic', '').strip()
    records = data.get('records', [])

    if not subject_id or not date_str or not records:
        return jsonify({'error': 'Subject ID, Date, and student records are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    subj = cursor.fetchone()
    if not subj:
        conn.close()
        return jsonify({'error': 'Subject not found'}), 404

    if date_str < SESSION_START_DATE:
        conn.close()
        return jsonify({'error': f'Cannot submit attendance before session start date ({SESSION_START_DATE}).'}), 400

    if is_weekend(date_str):
        w_name = get_weekend_name(date_str) or 'Weekend'
        conn.close()
        return jsonify({'error': f'Cannot submit attendance on {w_name} (College Holiday / Non-working day).'}), 400

    h_reason = get_holiday_reason(conn, date_str)
    if h_reason:
        conn.close()
        return jsonify({'error': f'Cannot submit attendance on holiday: {h_reason}'}), 400

    cursor.execute("SELECT id FROM subject_attendance WHERE subject_id = ? AND date = ? AND slot = ?",
                   (subject_id, date_str, slot))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': f'Attendance for {subj["code"]} ({slot}) has already been submitted for {date_str}.'}), 409

    faculty_id = session.get('faculty_id')
    submission_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        INSERT INTO subject_attendance (subject_id, faculty_id, year, date, slot, topic, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (subject_id, faculty_id, subj['year'], date_str, slot, topic, submission_time))
    att_id = cursor.lastrowid

    tuples = [(att_id, r['student_id'], r['status']) for r in records]
    cursor.executemany("""
        INSERT INTO subject_attendance_records (subject_attendance_id, student_id, status)
        VALUES (?, ?, ?)
    """, tuples)

    conn.commit()
    conn.close()

    return jsonify({
        'message': f'Subject attendance for {subj["code"]} - {subj["name"]} submitted successfully.',
        'subject_attendance_id': att_id,
        'subject_code': subj['code'],
        'date': date_str,
        'slot': slot,
        'total_marked': len(records)
    })

@app.route('/api/faculty/subject-attendance/history', methods=['GET'])
@login_required
def get_subject_attendance_history():
    subject_id = request.args.get('subject_id')
    faculty_id = session.get('faculty_id')
    role = session.get('role')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT sa.id, sa.subject_id, sa.faculty_id, sa.year, sa.date, sa.slot, sa.topic, sa.submitted_at,
               s.code as subject_code, s.name as subject_name, s.type as subject_type,
               f.name as faculty_name,
               COUNT(sar.id) as total_students,
               SUM(CASE WHEN sar.status = 'Present' THEN 1 ELSE 0 END) as present_count,
               SUM(CASE WHEN sar.status = 'Absent' THEN 1 ELSE 0 END) as absent_count
        FROM subject_attendance sa
        JOIN subjects s ON sa.subject_id = s.id
        LEFT JOIN faculty f ON sa.faculty_id = f.id
        LEFT JOIN subject_attendance_records sar ON sa.id = sar.subject_attendance_id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += " AND sa.subject_id = ?"
        params.append(subject_id)
    elif role != 'admin' and faculty_id:
        query += " AND sa.faculty_id = ?"
        params.append(faculty_id)

    query += " GROUP BY sa.id ORDER BY sa.date DESC, sa.submitted_at DESC LIMIT 30"
    cursor.execute(query, params)
    history = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({'history': history})

# 3. Admin Dashboard & Logs APIs
@app.route('/api/admin/dashboard', methods=['GET'])
@login_required
def get_admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total students and by year/branch
    cursor.execute("SELECT COUNT(*) as total FROM students WHERE status = 'active'")
    total_students = cursor.fetchone()['total']

    # Get distinct active classes from database
    cursor.execute("SELECT DISTINCT year FROM students WHERE status = 'active' ORDER BY year ASC")
    active_classes = [r['year'] for r in cursor.fetchall()]
    if not active_classes:
        active_classes = ['2nd Year (CSE)', '3rd Year (CSE)', '4th Year (CSE)', '4th Year (AI-DS)']

    year_counts = {}
    for yr in active_classes:
        cursor.execute("SELECT COUNT(*) as count FROM students WHERE year = ? AND status = 'active'", (yr,))
        year_counts[yr] = cursor.fetchone()['count']

    # Today's attendance status
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_status = {}
    for yr in active_classes:
        cursor.execute("""
            SELECT a.id, a.submitted_at, f.name as faculty_name
            FROM attendance a
            LEFT JOIN faculty f ON a.faculty_id = f.id
            WHERE a.year = ? AND a.date = ?
        """, (yr, today_str))
        row = cursor.fetchone()
        if row:
            today_status[yr] = {
                'status': 'Submitted',
                'faculty': row['faculty_name'] or 'Faculty',
                'submitted_at': row['submitted_at']
            }
        else:
            today_status[yr] = {
                'status': 'Pending',
                'faculty': None,
                'submitted_at': None
            }

    # Recent 8 attendance submissions
    cursor.execute("""
        SELECT a.id, a.year, a.date, a.submitted_at, f.name as faculty_name,
               COUNT(ar.id) as student_count,
               SUM(CASE WHEN ar.status = 'Present' THEN 1 ELSE 0 END) as present_count,
               SUM(CASE WHEN ar.status = 'Absent' THEN 1 ELSE 0 END) as absent_count
        FROM attendance a
        LEFT JOIN faculty f ON a.faculty_id = f.id
        LEFT JOIN attendance_records ar ON a.id = ar.attendance_id
        GROUP BY a.id
        ORDER BY a.date DESC, a.submitted_at DESC
        LIMIT 10
    """)
    recent_submissions = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        'total_students': total_students,
        'year_counts': year_counts,
        'today_date': today_str,
        'today_status': today_status,
        'recent_submissions': recent_submissions
    })

# 4. Student Management APIs
@app.route('/api/admin/students', methods=['GET'])
@login_required
def get_students():
    year = request.args.get('year')
    status = request.args.get('status')
    search = request.args.get('search', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if year:
        query += " AND year = ?"
        params.append(year)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (name LIKE ? OR roll_no LIKE ? OR enrollment_no LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY year ASC, CAST(roll_no AS INTEGER), roll_no ASC"
    cursor.execute(query, params)
    students = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({'students': students})

@app.route('/api/admin/students', methods=['POST'])
@admin_required
def add_student():
    data = request.get_json() or {}
    roll_no = str(data.get('roll_no', '')).strip()
    name = data.get('name', '').strip()
    enrollment_no = data.get('enrollment_no', '').strip()
    year = data.get('year', '').strip()
    status = data.get('status', 'active').strip()

    if not roll_no or not name or not year:
        return jsonify({'error': 'Roll No, Student Name, and Year/Branch are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (roll_no, name, enrollment_no, year, status)
            VALUES (?, ?, ?, ?, ?)
        """, (roll_no, name, enrollment_no, year, status))
        conn.commit()
        student_id = cursor.lastrowid
        conn.close()
        return jsonify({'message': 'Student added successfully', 'id': student_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': f'Roll No {roll_no} already exists in {year}'}), 409

@app.route('/api/admin/students/<int:student_id>', methods=['PUT'])
@admin_required
def update_student(student_id):
    data = request.get_json() or {}
    roll_no = str(data.get('roll_no', '')).strip()
    name = data.get('name', '').strip()
    enrollment_no = data.get('enrollment_no', '').strip()
    year = data.get('year', '').strip()
    status = data.get('status', 'active').strip()

    if not roll_no or not name or not year:
        return jsonify({'error': 'Roll No, Student Name, and Year are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE students
            SET roll_no = ?, name = ?, enrollment_no = ?, year = ?, status = ?
            WHERE id = ?
        """, (roll_no, name, enrollment_no, year, status, student_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Student updated successfully'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': f'Roll No {roll_no} already exists in {year}'}), 409

@app.route('/api/admin/students/<int:student_id>', methods=['DELETE'])
@admin_required
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Student deleted successfully'})

@app.route('/api/admin/students/import', methods=['POST'])
@admin_required
def import_students():
    """
    Import students via JSON array or CSV/Excel file.
    Accepts: { students: [{roll_no, name, year, enrollment_no}] } or multipart file
    """
    students_to_add = []

    if 'file' in request.files:
        file = request.files['file']
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
            reader = csv.DictReader(stream)
            for row in reader:
                roll = row.get('Roll No') or row.get('roll_no') or row.get('Roll') or row.get('RollNo')
                name = row.get('Student Name') or row.get('name') or row.get('Name') or row.get('Student')
                yr = row.get('Year') or row.get('year') or row.get('Class')
                enr = row.get('Enrollment No') or row.get('enrollment_no') or row.get('Enrollment') or ''
                if roll and name and yr:
                    yr_norm = str(yr).strip()
                    s_low = yr_norm.lower()
                    e_low = str(enr).lower()
                    if 'ai' in s_low or 'aids' in s_low or 'ai-ds' in s_low or 'ad' in e_low:
                        yr_norm = '4th Year (AI-DS)'
                    elif '4' in s_low or '7' in s_low:
                        yr_norm = '4th Year (CSE)'
                    elif '3' in s_low or '5' in s_low:
                        yr_norm = '3rd Year (CSE)'
                    elif '2' in s_low:
                        yr_norm = '2nd Year (CSE)'
                    students_to_add.append({
                        'roll_no': str(roll).strip(),
                        'name': str(name).strip(),
                        'year': yr_norm,
                        'enrollment_no': str(enr).strip(),
                        'status': 'active'
                    })
        elif filename.endswith(('.xlsx', '.xls')):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            headers = [str(cell.value).strip() if cell.value is not None else '' for cell in sheet[1]]
            for row_cells in sheet.iter_rows(min_row=2, values_only=True):
                if not any(row_cells):
                    continue
                row_dict = {headers[i]: row_cells[i] for i in range(min(len(headers), len(row_cells)))}
                roll = row_dict.get('Roll No') or row_dict.get('roll_no') or row_dict.get('Roll') or (row_cells[0] if len(row_cells)>0 else None)
                name = row_dict.get('Student Name') or row_dict.get('name') or row_dict.get('Name') or (row_cells[1] if len(row_cells)>1 else None)
                yr = row_dict.get('Year') or row_dict.get('year') or (row_cells[2] if len(row_cells)>2 else None)
                enr = row_dict.get('Enrollment No') or row_dict.get('enrollment_no') or (row_cells[3] if len(row_cells)>3 else '')
                if roll and name and yr:
                    yr_norm = str(yr).strip()
                    s_low = yr_norm.lower()
                    e_low = str(enr).lower()
                    if 'ai' in s_low or 'aids' in s_low or 'ai-ds' in s_low or 'ad' in e_low:
                        yr_norm = '4th Year (AI-DS)'
                    elif '4' in s_low or '7' in s_low:
                        yr_norm = '4th Year (CSE)'
                    elif '3' in s_low or '5' in s_low:
                        yr_norm = '3rd Year (CSE)'
                    elif '2' in s_low:
                        yr_norm = '2nd Year (CSE)'
                    students_to_add.append({
                        'roll_no': str(roll).strip(),
                        'name': str(name).strip(),
                        'year': yr_norm,
                        'enrollment_no': str(enr).strip() if enr else '',
                        'status': 'active'
                    })
    else:
        data = request.get_json() or {}
        students_to_add = data.get('students', [])

    if not students_to_add:
        return jsonify({'error': 'No valid student records found in payload or file.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    inserted_count = 0
    skipped_count = 0

    for s in students_to_add:
        roll = str(s.get('roll_no', '')).strip()
        name = str(s.get('name', '')).strip()
        yr = str(s.get('year', '')).strip()
        enr = str(s.get('enrollment_no', '')).strip()
        status = str(s.get('status', 'active')).strip()
        if not roll or not name or not yr:
            skipped_count += 1
            continue
        try:
            cursor.execute("""
                INSERT INTO students (roll_no, name, enrollment_no, year, status)
                VALUES (?, ?, ?, ?, ?)
            """, (roll, name, enr, yr, status))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # Update existing or skip
            cursor.execute("""
                UPDATE students SET name = ?, enrollment_no = ?, status = ?
                WHERE roll_no = ? AND year = ?
            """, (name, enr, status, roll, yr))
            inserted_count += 1

    conn.commit()
    conn.close()

    return jsonify({
        'message': f'Successfully processed {inserted_count} students ({skipped_count} skipped).',
        'imported_count': inserted_count,
        'skipped_count': skipped_count
    })

# 5. Faculty Management APIs
@app.route('/api/admin/faculty', methods=['GET'])
@admin_required
def get_faculty():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.name, f.email, f.phone, f.assigned_year, u.username
        FROM faculty f
        LEFT JOIN users u ON u.faculty_id = f.id
        ORDER BY f.assigned_year ASC
    """)
    faculties = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'faculty': faculties})

@app.route('/api/admin/faculty/<int:faculty_id>', methods=['PUT'])
@admin_required
def update_faculty(faculty_id):
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    assigned_year = data.get('assigned_year', '').strip()
    password = data.get('password', '').strip()

    if not name or not email or not assigned_year:
        return jsonify({'error': 'Name, Email, and Assigned Year are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if another faculty already has this assigned year
    cursor.execute("SELECT id, name FROM faculty WHERE assigned_year = ? AND id != ?", (assigned_year, faculty_id))
    existing_faculty = cursor.fetchone()
    if existing_faculty:
        conn.close()
        return jsonify({'error': f'{assigned_year} is already assigned to {existing_faculty["name"]}. Each year must have exactly 1 faculty.'}), 400

    try:
        cursor.execute("""
            UPDATE faculty
            SET name = ?, email = ?, phone = ?, assigned_year = ?
            WHERE id = ?
        """, (name, email, phone, assigned_year, faculty_id))

        if password:
            pass_hash = generate_password_hash(password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE faculty_id = ?", (pass_hash, faculty_id))

        conn.commit()
        conn.close()
        return jsonify({'message': 'Faculty updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to update faculty: {str(e)}'}), 400

# 5.1 Admin Subject & Allocation APIs
@app.route('/api/admin/subjects', methods=['GET'])
@login_required
def get_admin_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.code, s.name, s.type, s.year, s.department, s.semester,
               GROUP_CONCAT(f.name, ', ') as faculty_names,
               GROUP_CONCAT(f.id, ',') as faculty_ids
        FROM subjects s
        LEFT JOIN subject_allocations sa ON s.id = sa.subject_id
        LEFT JOIN faculty f ON sa.faculty_id = f.id
        GROUP BY s.id
        ORDER BY s.department ASC, s.semester ASC, s.code ASC, s.type ASC
    """)
    rows = cursor.fetchall()
    subjects = []
    for r in rows:
        f_ids = [int(x) for x in r['faculty_ids'].split(',') if x] if r['faculty_ids'] else []
        cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE year = ? AND status = 'active'", (r['year'],))
        cnt = cursor.fetchone()['cnt']
        subjects.append({
            'id': r['id'],
            'code': r['code'],
            'name': r['name'],
            'type': r['type'],
            'year': r['year'],
            'department': r['department'],
            'semester': r['semester'],
            'faculty_names': r['faculty_names'] or 'Unallocated',
            'faculty_ids': f_ids,
            'student_count': cnt
        })
    conn.close()
    return jsonify({'subjects': subjects})

@app.route('/api/admin/subjects', methods=['POST'])
@admin_required
def add_admin_subject():
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    name = data.get('name', '').strip()
    stype = data.get('type', 'Theory').strip()
    year = data.get('year', '').strip()
    department = data.get('department', 'CSE').strip()
    semester = data.get('semester', 'III').strip()
    faculty_ids = data.get('faculty_ids', [])

    if not code or not name or not year:
        return jsonify({'error': 'Subject Code, Name, and Year/Branch are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO subjects (code, name, type, year, department, semester)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, name, stype, year, department, semester))
        subject_id = cursor.lastrowid

        for fid in faculty_ids:
            cursor.execute("""
                INSERT OR IGNORE INTO subject_allocations (subject_id, faculty_id, role)
                VALUES (?, ?, 'Primary')
            """, (subject_id, fid))

        conn.commit()
        conn.close()
        return jsonify({'message': f'Subject {code} added successfully', 'id': subject_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to add subject: {str(e)}'}), 400

@app.route('/api/admin/subjects/<int:subject_id>', methods=['PUT'])
@admin_required
def update_admin_subject(subject_id):
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    name = data.get('name', '').strip()
    stype = data.get('type', 'Theory').strip()
    year = data.get('year', '').strip()
    department = data.get('department', 'CSE').strip()
    semester = data.get('semester', 'III').strip()
    faculty_ids = data.get('faculty_ids', [])

    if not code or not name or not year:
        return jsonify({'error': 'Subject Code, Name, and Year/Branch are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE subjects
            SET code = ?, name = ?, type = ?, year = ?, department = ?, semester = ?
            WHERE id = ?
        """, (code, name, stype, year, department, semester, subject_id))

        if isinstance(faculty_ids, list):
            cursor.execute("DELETE FROM subject_allocations WHERE subject_id = ?", (subject_id,))
            for fid in faculty_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO subject_allocations (subject_id, faculty_id, role)
                    VALUES (?, ?, 'Primary')
                """, (subject_id, fid))

        conn.commit()
        conn.close()
        return jsonify({'message': 'Subject updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to update subject: {str(e)}'}), 400

@app.route('/api/admin/subjects/<int:subject_id>', methods=['DELETE'])
@admin_required
def delete_admin_subject(subject_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Subject deleted successfully'})

@app.route('/api/admin/subjects/allocate', methods=['POST'])
@admin_required
def allocate_subject():
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    faculty_ids = data.get('faculty_ids', [])

    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subject_allocations WHERE subject_id = ?", (subject_id,))
    for fid in faculty_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO subject_allocations (subject_id, faculty_id, role)
            VALUES (?, ?, 'Primary')
        """, (subject_id, fid))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Faculty allocations updated successfully'})

# 6. Holiday Management APIs
@app.route('/api/admin/holidays', methods=['GET'])
@login_required
def get_holidays():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, reason FROM holidays ORDER BY date ASC")
    holidays = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'holidays': holidays})

@app.route('/api/admin/holidays', methods=['POST'])
@admin_required
def add_holiday():
    data = request.get_json() or {}
    date_str = data.get('date', '').strip()
    reason = data.get('reason', '').strip()

    if not date_str or not reason:
        return jsonify({'error': 'Date and Reason are required'}), 400

    # Validate date format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO holidays (date, reason) VALUES (?, ?)", (date_str, reason))
        conn.commit()
        h_id = cursor.lastrowid
        conn.close()
        return jsonify({'message': 'Holiday added successfully', 'id': h_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': f'Holiday for {date_str} already exists'}), 409

@app.route('/api/admin/holidays/<int:holiday_id>', methods=['DELETE'])
@admin_required
def delete_holiday(holiday_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Holiday deleted successfully'})

# 7. Attendance Log & Detail Management (Admin edit)
@app.route('/api/admin/attendance-detail/<int:attendance_id>', methods=['GET'])
@login_required
def get_attendance_detail(attendance_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.year, a.date, a.submitted_at, f.name as faculty_name
        FROM attendance a
        LEFT JOIN faculty f ON a.faculty_id = f.id
        WHERE a.id = ?
    """, (attendance_id,))
    att = cursor.fetchone()
    if not att:
        conn.close()
        return jsonify({'error': 'Attendance record not found'}), 404

    cursor.execute("""
        SELECT ar.id as record_id, ar.student_id, ar.status, s.roll_no, s.name, s.enrollment_no
        FROM attendance_records ar
        JOIN students s ON ar.student_id = s.id
        WHERE ar.attendance_id = ?
        ORDER BY CAST(s.roll_no AS INTEGER), s.roll_no ASC
    """, (attendance_id,))
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({
        'attendance': dict(att),
        'records': records
    })

@app.route('/api/admin/attendance-detail/<int:attendance_id>', methods=['PUT'])
@admin_required
def update_attendance_detail(attendance_id):
    data = request.get_json() or {}
    records = data.get('records', []) # [{'student_id': 1, 'status': 'Present'}]

    if not records:
        return jsonify({'error': 'No records provided'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    for r in records:
        cursor.execute("""
            UPDATE attendance_records
            SET status = ?
            WHERE attendance_id = ? AND student_id = ?
        """, (r['status'], attendance_id, r['student_id']))

    # Update timestamp
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("UPDATE attendance SET submitted_at = ? WHERE id = ?", (now_str, attendance_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Attendance updated successfully by Admin.'})

# 8. Dynamic Attendance Report Engine (15-Day, 30-Day, Custom Range)
def generate_report_data(conn, year, start_date_str, end_date_str):
    """
    Computes working dates (excluding Sundays & Holidays) and generates the full matrix.
    Attendance % = (Present Count / Total Working Days) * 100
    """
    working_dates = get_working_dates(conn, start_date_str, end_date_str)
    cursor = conn.cursor()

    # Get active students for year
    cursor.execute("""
        SELECT id, roll_no, name, enrollment_no
        FROM students
        WHERE year = ? AND status = 'active'
        ORDER BY CAST(roll_no AS INTEGER), roll_no ASC
    """, (year,))
    students = [dict(r) for r in cursor.fetchall()]

    total_working_days = len(working_dates)
    total_students_count = len(students)

    if not working_dates or not students:
        return {
            'year': year,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'working_dates': working_dates,
            'students_report': [],
            'summary': {
                'total_working_days': total_working_days,
                'total_students': total_students_count,
                'class_average_percentage': 0.0
            }
        }

    # Fetch all attendance records for this year in the date range
    placeholders = ','.join(['?'] * len(working_dates))
    query = f"""
        SELECT a.date, ar.student_id, ar.status
        FROM attendance a
        JOIN attendance_records ar ON a.id = ar.attendance_id
        WHERE a.year = ? AND a.date IN ({placeholders})
    """
    cursor.execute(query, [year] + working_dates)
    rows = cursor.fetchall()

    # Map (student_id, date) -> status ('Present' or 'Absent')
    att_map = {}
    for r in rows:
        att_map[(r['student_id'], r['date'])] = r['status']

    students_report = []
    total_class_p = 0
    total_class_a = 0

    for s in students:
        s_id = s['id']
        date_records = {}
        present_count = 0
        absent_count = 0

        for d in working_dates:
            st = att_map.get((s_id, d), '-') # '-' if class wasn't conducted or student wasn't marked
            date_records[d] = st
            if st == 'Present':
                present_count += 1
            elif st == 'Absent':
                absent_count += 1

        if total_working_days > 0:
            pct = round((present_count / total_working_days) * 100, 2)
        else:
            pct = 0.0

        total_class_p += present_count
        total_class_a += absent_count

        students_report.append({
            'id': s['id'],
            'roll_no': s['roll_no'],
            'name': s['name'],
            'enrollment_no': s['enrollment_no'] or '-',
            'dates': date_records,
            'present_count': present_count,
            'absent_count': absent_count,
            'total_conducted': total_working_days,
            'percentage': pct
        })

    max_possible_slots = total_students_count * total_working_days
    class_avg = round((total_class_p / max_possible_slots * 100), 2) if max_possible_slots > 0 else 0.0

    return {
        'year': year,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'working_dates': working_dates,
        'students_report': students_report,
        'summary': {
            'total_working_days': total_working_days,
            'total_students': total_students_count,
            'class_average_percentage': class_avg
        }
    }

@app.route('/api/reports/attendance', methods=['GET'])
@login_required
def get_attendance_report():
    year = request.args.get('year', '3rd Year (CSE)')
    preset = request.args.get('preset') # 'session', '15', '30', or 'custom'
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # If faculty, lock to assigned year
    if session.get('role') == 'faculty':
        year = session.get('assigned_year')

    today = datetime.now().date()
    if preset == 'session' or not preset:
        start_date = SESSION_START_DATE
        end_date = today.strftime('%Y-%m-%d')
    elif preset == '15':
        calc_start = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        start_date = max(calc_start, SESSION_START_DATE)
        end_date = today.strftime('%Y-%m-%d')
    elif preset == '30':
        calc_start = (today - timedelta(days=29)).strftime('%Y-%m-%d')
        start_date = max(calc_start, SESSION_START_DATE)
        end_date = today.strftime('%Y-%m-%d')
    elif preset == 'custom':
        if not start_date:
            start_date = SESSION_START_DATE
        if not end_date:
            end_date = today.strftime('%Y-%m-%d')
    else:
        start_date = SESSION_START_DATE
        end_date = today.strftime('%Y-%m-%d')

    if start_date < SESSION_START_DATE:
        start_date = SESSION_START_DATE

    conn = get_db_connection()
    report_data = generate_report_data(conn, year, start_date, end_date)
    conn.close()

    return jsonify(report_data)

@app.route('/api/reports/export/excel', methods=['GET'])
@login_required
def export_excel_report():
    year = request.args.get('year', '3rd Year (CSE)')
    preset = request.args.get('preset')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if session.get('role') == 'faculty':
        year = session.get('assigned_year')

    today = datetime.now().date()
    if preset == 'session' or not preset:
        start_date = SESSION_START_DATE
        end_date = today.strftime('%Y-%m-%d')
    elif preset == '15':
        calc_start = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        start_date = max(calc_start, SESSION_START_DATE)
        end_date = today.strftime('%Y-%m-%d')
    elif preset == '30':
        calc_start = (today - timedelta(days=29)).strftime('%Y-%m-%d')
        start_date = max(calc_start, SESSION_START_DATE)
        end_date = today.strftime('%Y-%m-%d')
    elif preset == 'custom':
        if not start_date:
            start_date = SESSION_START_DATE
        if not end_date:
            end_date = today.strftime('%Y-%m-%d')
    else:
        start_date = SESSION_START_DATE
        end_date = today.strftime('%Y-%m-%d')

    if start_date < SESSION_START_DATE:
        start_date = SESSION_START_DATE

    conn = get_db_connection()
    report = generate_report_data(conn, year, start_date, end_date)
    conn.close()

    # Build Excel using openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{year} Attendance"

    # Styling definitions
    title_font = Font(name='Arial', size=16, bold=True, color='1E293B')
    subtitle_font = Font(name='Arial', size=11, italic=True, color='64748B')
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid') # Navy
    summary_fill = PatternFill(start_color='0284C7', end_color='0284C7', fill_type='solid') # Sky
    data_font = Font(name='Arial', size=10)
    present_font = Font(name='Arial', size=10, bold=True, color='047857') # Emerald
    absent_font = Font(name='Arial', size=10, bold=True, color='B91C1C') # Rose
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    # 1. Report Title & Info
    ws.merge_cells('A1:H1')
    ws['A1'] = f"Student Attendance Management Report - {year}"
    ws['A1'].font = title_font
    ws['A1'].alignment = align_left

    ws.merge_cells('A2:H2')
    ws['A2'] = f"Date Range: {start_date} to {end_date} | Working Days (Excluding Saturdays, Sundays & Holidays): {report['summary']['total_working_days']} | Class Avg: {report['summary']['class_average_percentage']}%"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = align_left

    # 2. Table Headers
    headers = ["Roll No", "Student Name", "Enrollment No"]
    # Format date headers as 'DD MMM'
    date_headers = []
    for d in report['working_dates']:
        try:
            d_fmt = datetime.strptime(d, '%Y-%m-%d').strftime('%d %b')
        except:
            d_fmt = d
        date_headers.append(d_fmt)
    headers.extend(date_headers)
    headers.extend(["Present", "Absent", "Percentage (%)"])

    header_row = 4
    for col_idx, h_text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=h_text)
        cell.font = header_font
        if col_idx > len(headers) - 3:
            cell.fill = summary_fill
        else:
            cell.fill = header_fill
        cell.alignment = align_center
        cell.border = border_thin

    # 3. Data Rows
    current_row = 5
    for s in report['students_report']:
        # Roll No
        c1 = ws.cell(row=current_row, column=1, value=s['roll_no'])
        c1.alignment = align_center; c1.font = data_font; c1.border = border_thin
        # Name
        c2 = ws.cell(row=current_row, column=2, value=s['name'])
        c2.alignment = align_left; c2.font = data_font; c2.border = border_thin
        # Enrollment
        c3 = ws.cell(row=current_row, column=3, value=s['enrollment_no'])
        c3.alignment = align_center; c3.font = data_font; c3.border = border_thin

        # Dates
        col_offset = 4
        for d in report['working_dates']:
            val = s['dates'].get(d, '-')
            short_val = 'P' if val == 'Present' else ('A' if val == 'Absent' else '-')
            c_date = ws.cell(row=current_row, column=col_offset, value=short_val)
            c_date.alignment = align_center
            c_date.border = border_thin
            if short_val == 'P':
                c_date.font = present_font
            elif short_val == 'A':
                c_date.font = absent_font
            else:
                c_date.font = data_font
            col_offset += 1

        # Summary columns
        cp = ws.cell(row=current_row, column=col_offset, value=s['present_count'])
        cp.alignment = align_center; cp.font = present_font; cp.border = border_thin

        ca = ws.cell(row=current_row, column=col_offset+1, value=s['absent_count'])
        ca.alignment = align_center; ca.font = absent_font; ca.border = border_thin

        cpct = ws.cell(row=current_row, column=col_offset+2, value=f"{s['percentage']}%")
        cpct.alignment = align_center; cpct.font = Font(name='Arial', size=10, bold=True); cpct.border = border_thin

        current_row += 1

    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)
    ws.column_dimensions['A'].width = 10
    ws.column_dimensions['B'].width = 24
    ws.column_dimensions['C'].width = 16

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Attendance_Report_{year.replace(' ', '_')}_{start_date}_to_{end_date}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
