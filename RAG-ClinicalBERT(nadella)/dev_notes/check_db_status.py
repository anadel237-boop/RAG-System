import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn_str = os.getenv('NEON_CONNECTION_STRING')
if not conn_str:
    print("❌ NEON_CONNECTION_STRING not found")
    exit(1)

try:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    
    # Check total cases
    cursor.execute("SELECT COUNT(*) FROM medical_cases")
    total = cursor.fetchone()[0]
    print(f"Total cases: {total}")
    
    # Check cases with embeddings
    cursor.execute("SELECT COUNT(*) FROM medical_cases WHERE embedding IS NOT NULL")
    with_embeddings = cursor.fetchone()[0]
    print(f"Cases with embeddings: {with_embeddings}")
    
    # Check a sample embedding
    if with_embeddings > 0:
        cursor.execute("SELECT case_id, substring(content, 1, 50) FROM medical_cases WHERE embedding IS NOT NULL LIMIT 1")
        sample = cursor.fetchone()
        print(f"Sample case: {sample}")
    
    conn.close()
except Exception as e:
    print(f"❌ Database error: {e}")
