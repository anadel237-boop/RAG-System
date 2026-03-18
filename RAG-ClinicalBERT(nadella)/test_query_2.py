import requests

base_url = 'http://localhost:5557'
session = requests.Session()
session.post(f'{base_url}/login', data={'username': 'admin', 'password': 'medical_rag_2025'})

queries = [
    "What medications are prescribed for hypertension?",
    "Patient presents with chest pain and shortness of breath. What could be the diagnosis?"
]

for q in queries:
    print(f"\n🧠 Query: {q}")
    response = session.post(f'{base_url}/api/medical_query', json={'query': q})
    if response.status_code == 200:
        print("\n📝 Answer:")
        print("-" * 50)
        print(response.json().get('answer'))
        print("-" * 50)
