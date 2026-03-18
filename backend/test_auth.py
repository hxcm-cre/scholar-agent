import requests

BASE_URL = "http://127.0.0.1:8000"

def test_auth():
    print("Testing Registration...")
    res = requests.post(f"{BASE_URL}/api/auth/register", json={"username": "testuser", "password": "password123"})
    print("Register:", res.status_code, res.json())

    print("\nTesting Login...")
    res = requests.post(f"{BASE_URL}/api/auth/login", data={"username": "testuser", "password": "password123"})
    print("Login:", res.status_code, res.json())
    
    if res.status_code == 200:
        token = res.json().get("access_token")
        print("\nTesting Me (Get Current User)...")
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        print("Me:", res.status_code, res.json())

        print("\nTesting Admin Users (Should be allowed for first user)...")
        res = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        print("Admin Users:", res.status_code, res.json())
        
        print("\nTesting Create Project...")
        res = requests.post(f"{BASE_URL}/api/research", headers=headers, json={"query": "test project query"})
        print("Create Project:", res.status_code, res.json())

        print("\nTesting List Projects...")
        res = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        print("List Projects:", res.status_code, res.json())

test_auth()
