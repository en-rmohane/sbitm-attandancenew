from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

def inspect_and_sync_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.password_hash, u.role, u.faculty_id, f.name as faculty_name
        FROM users u
        LEFT JOIN faculty f ON u.faculty_id = f.id
        ORDER BY u.id ASC
    """)
    users = cursor.fetchall()
    print(f"Total Users in Database: {len(users)}\n" + "="*60)
    
    updates = 0
    for u in users:
        u_name = u['username']
        f_name = u['faculty_name'] or 'N/A'
        p_hash = u['password_hash']
        
        matches_112233 = check_password_hash(p_hash, '112233')
        matches_admin = check_password_hash(p_hash, 'admin123') if u_name == 'admin' else False
        
        print(f"ID: {u['id']:<3} | User: {u_name:<15} | Role: {u['role']:<8} | Faculty: {f_name:<25} | Pass '112233': {matches_112233}")
        
        if not matches_112233:
            new_hash = generate_password_hash('112233')
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, u['id']))
            updates += 1
            print(f"  -> FIXED password for '{u_name}' to '112233'")
            
    conn.commit()
    print("="*60)
    print(f"Password reset completed. {updates} user accounts were updated to '112233'.")

if __name__ == '__main__':
    inspect_and_sync_all_users()
