import requests
import json

# Login credentials (replace with actual admin credentials)
login_data = {
    "username": "admin",
    "password": "1234"
}

# Login to get session
session = requests.Session()

print("Logging in...")
response = session.post(
    "http://localhost:8000/auth/login",
    json=login_data,
    headers={"Content-Type": "application/json"}
)

if response.ok:
    print("✓ Login successful!")
    print(f"Response: {response.json()}")
    
    # Get session cookie
    session_cookie = session.cookies.get_dict()
    print(f"\nSession cookies: {session_cookie}")
    
    # Save cookies to file
    with open('cookies.txt', 'w') as f:
        for cookie in session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")
    
    print("\n✓ Cookies saved to cookies.txt")
    
    # Now test duplicate bill endpoint
    print("\n--- Testing Duplicate Bill API ---")
    response = session.get(
        "http://localhost:8000/duplicatebill/search?page=1&limit=8",
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
else:
    print(f"✗ Login failed: {response.status_code}")
    print(f"Response: {response.text}")
