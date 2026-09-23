from database import get_db_connection
from app import app

def verify_aids_students():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Check 4th Year (AI-DS)
    cur.execute("SELECT roll_no, name, enrollment_no FROM students WHERE year = '4th Year (AI-DS)' ORDER BY CAST(roll_no AS INTEGER)")
    final_students = cur.fetchall()
    print(f"============================================================")
    print(f"4th Year (AI-DS) Final Year Students: {len(final_students)} (Expected 18)")
    print(f"============================================================")
    for s in final_students:
        print(f"  Roll: {s['roll_no']:<3} | Enroll: {s['enrollment_no']:<15} | Name: {s['name']}")
    assert len(final_students) == 18, f"Expected 18, got {len(final_students)}"

    # 2. Check 3rd Year (AI-DS)
    cur.execute("SELECT roll_no, name, enrollment_no FROM students WHERE year = '3rd Year (AI-DS)' ORDER BY CAST(roll_no AS INTEGER)")
    third_students = cur.fetchall()
    print(f"\n============================================================")
    print(f"3rd Year (AI-DS) Students: {len(third_students)} (Expected 28)")
    print(f"============================================================")
    for s in third_students:
        print(f"  Roll: {s['roll_no']:<3} | Enroll: {s['enrollment_no']:<15} | Name: {s['name']}")
    assert len(third_students) == 28, f"Expected 28, got {len(third_students)}"

    # 3. Check Subject loading via Flask API
    client = app.test_client()
    
    # Check subjects for Ashish Gawande (ML & Data Viz)
    with client.session_transaction() as sess:
        sess['user_id'] = 8
        sess['username'] = 'ashish'
        sess['role'] = 'faculty'
        sess['faculty_id'] = 8
        sess['assigned_year'] = '3rd Year (AI-DS)'
        sess['display_name'] = 'Prof. Ashish Gawande'
        
    res = client.get('/api/faculty/my-subjects')
    data = res.get_json()
    subjects = data.get('subjects', [])
    print(f"\nProf. Ashish Gawande Subjects: {len(subjects)}")
    for s in subjects:
        print(f"  - [{s['code']}] {s['name']} ({s['type']}) -> {s['year']}: {s['student_count']} students")
        
    print("\nALL VERIFICATIONS PASSED 100%!")
    conn.close()

if __name__ == '__main__':
    verify_aids_students()
