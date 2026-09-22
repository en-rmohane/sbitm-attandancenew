import requests
import json
from app import app

client = app.test_client()

def test_logins():
    users_to_test = [
        ('admin', '112233'),
        ('admin', 'admin123'),
        ('ravi', '112233'),
        ('satish', '112233'),
        ('sonali', '112233'),
        ('alka', '112233'),
        ('khushbu', '112233'),
        ('ashish', '112233'),
        ('jeet', '112233'),
        ('bhavesh', '112233'),
        ('nilesh', '112233'),
        ('pankaj', '112233'),
        ('shashank', '112233'),
        ('rishu', '112233'),
        ('malvi', '112233'),
        ('deepika', '112233'),
        ('pushpa', '112233'),
        ('pramila', '112233'),
        ('pjshah', '112233'),
        ('vinay', '112233'),
    ]
    
    print("Testing all logins on test client...")
    passed = 0
    for u, p in users_to_test:
        resp = client.post('/api/auth/login', json={'username': u, 'password': p})
        if resp.status_code == 200:
            data = resp.get_json()
            print(f"  [OK] User: {u:<10} Pass: {p:<10} -> Name: {data['user']['name']} ({data['user']['role']})")
            passed += 1
        else:
            print(f"  [FAIL] User: {u:<10} Pass: {p:<10} -> Status: {resp.status_code} Error: {resp.get_json()}")
            
    print(f"\nResult: {passed}/{len(users_to_test)} passed!")

if __name__ == '__main__':
    test_logins()
