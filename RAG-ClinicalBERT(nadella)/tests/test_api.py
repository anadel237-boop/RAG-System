
import requests
import json

def test_api():
    base_url = "http://127.0.0.1:5557"
    login_url = f"{base_url}/login"
    query_url = f"{base_url}/api/medical_query"
    
    # Credentials (default)
    credentials = {
        "username": "admin",
        "password": "medical_rag_2025"
    }

    session = requests.Session()

    try:
        # Step 1: Login
        print("🔐 Logging in...")
        login_response = session.post(login_url, data=credentials)
        
        if login_response.status_code == 200:
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            return

        # Step 2: Query API
        print("📨 Sending query...")
        payload = {
            "query": "patient with chest pain"
        }
        headers = {
            "Content-Type": "application/json"
        }
        
        response = session.post(query_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", True):
                print("✅ API Query Successful")
                print(f"Answer: {data.get('answer')[:100]}...")
                
                # Check relevant cases count (API returns an integer count)
                cases_count = data.get('relevant_cases', 0)
                print(f"Relevant Cases Found: {cases_count}")
                
                if cases_count > 0:
                     print("✅ Retrieval working correctly")
                else:
                     print("⚠️ No relevant cases returned.")
            else:
                print(f"❌ API Error: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_api()
