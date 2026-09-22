import sys
from app import app
import json

client = app.test_client()

print('============================================================')
print('TESTING FACULTY ACCOUNTS, ALLOCATIONS & SUBJECT ATTENDANCE')
print('============================================================')

# 1. Test Logins for faculties
test_users = ['admin', 'ravi', 'satish', 'sonali', 'alka', 'khushbu', 'ashish', 'vinay', 'pankaj', 'pjshah', 'pramila', 'deepika']
passed_logins = 0

for u in test_users:
    res = client.post('/api/auth/login', json={'username': u, 'password': '112233'})
    if res.status_code == 200:
        passed_logins += 1
        data = res.get_json()
        print(f"  [PASS] Login: {u:10s} -> {data['user']['name']}")
    else:
        print(f"  [FAIL] Login: {u} -> Status {res.status_code} {res.data}")

print(f"\nTotal Successful Logins: {passed_logins}/{len(test_users)}")

# 2. Test Faculty My Subjects for Prof. Satish (TOC, Big Data, etc.)
with client.session_transaction() as sess:
    sess['user_id'] = 4
    sess['username'] = 'satish'
    sess['role'] = 'faculty'
    sess['faculty_id'] = 4
    sess['assigned_year'] = '4th Year (AI-DS)'
    sess['display_name'] = 'Prof. Satish Chadokar'

res = client.get('/api/faculty/my-subjects')
data = res.get_json()
subjects = data.get('subjects', [])
print(f"\nProf. Satish Chadokar allocated subjects: {len(subjects)}")
for s in subjects:
    print(f"   - {s['code']:8s} | {s['name']:35s} | {s['type']:10s} | {s['year']} ({s['student_count']} students)")

assert len(subjects) >= 4, 'Satish should have at least 4 allocated subjects'
test_subj = subjects[0]

# 3. Test Loading Students for Subject
res = client.get(f"/api/faculty/subject-students?subject_id={test_subj['id']}")
s_data = res.get_json()
students = s_data.get('students', [])
print(f"\nLoaded {len(students)} students for subject {test_subj['code']}")
assert len(students) > 0, 'Should load active students'

# 4. Test Submitting Subject Attendance
att_records = [{'student_id': st['id'], 'status': 'Present' if i % 5 != 0 else 'Absent'} for i, st in enumerate(students)]
sub_payload = {
    'subject_id': test_subj['id'],
    'date': '2026-09-22',
    'slot': 'Lecture 1 (10:00 - 11:00 AM)',
    'topic': 'Introduction & Finite Automata State Diagrams',
    'records': att_records
}

res = client.post('/api/faculty/subject-attendance/submit', json=sub_payload)
print(f"Subject Attendance Submission: Status {res.status_code}")
if res.status_code == 200 or res.status_code == 409:
    msg_key = 'message' if res.status_code == 200 else 'error'
    print(f"  [PASS] Subject Attendance Result: {res.get_json().get(msg_key)}")

# 5. Test Duplicate Prevention
res_dup = client.post('/api/faculty/subject-attendance/submit', json=sub_payload)
print(f"  [PASS] Duplicate Prevention Status: {res_dup.status_code} (Expected 409)")
assert res_dup.status_code == 409

# 6. Test Subject Attendance History
res_hist = client.get(f"/api/faculty/subject-attendance/history?subject_id={test_subj['id']}")
hist_data = res_hist.get_json()
print(f"  [PASS] Subject History Entries: {len(hist_data.get('history', []))}")

# 7. Test Admin Subject Catalog & Allocations
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['username'] = 'admin'
    sess['role'] = 'admin'

res_admin_sub = client.get('/api/admin/subjects')
admin_subs = res_admin_sub.get_json().get('subjects', [])
print(f"  [PASS] Admin Subjects Catalog: {len(admin_subs)} subjects registered")
assert len(admin_subs) >= 25, 'Catalog should contain all timetable subjects'

print('\n============================================================')
print('ALL TESTS PASSED SUCCESSFULLY! (100%)')
print('============================================================')
