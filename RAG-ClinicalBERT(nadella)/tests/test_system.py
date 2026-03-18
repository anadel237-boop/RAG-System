#!/usr/bin/env python3
"""
Test the Medical RAG System for errors without starting the web server
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test imports
print("✓ Testing imports...")
try:
    import optimized_medical_rag_system as rag_module
    print("✓ Successfully imported optimized_medical_rag_system")
except Exception as e:
    print(f"✗ Error importing optimized_medical_rag_system: {e}")
    sys.exit(1)

# Test environment variables
print("\n✓ Testing environment variables...")
neon_connection = os.getenv('NEON_CONNECTION_STRING')
openai_key = os.getenv('OPENAI_API_KEY')

if not neon_connection:
    print("✗ NEON_CONNECTION_STRING not found in environment")
    sys.exit(1)
else:
    print("✓ NEON_CONNECTION_STRING is set")

if not openai_key:
    print("✗ OPENAI_API_KEY not found in environment")
    sys.exit(1)
else:
    print("✓ OPENAI_API_KEY is set")

# Test data directory
print("\n✓ Testing data directory...")
data_dir = os.path.join(os.getcwd(), "data")
if not os.path.exists(data_dir):
    print(f"✗ Data directory not found: {data_dir}")
    sys.exit(1)

case_files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
print(f"✓ Found {len(case_files)} case files in data directory")

# Test RAG system initialization
print("\n✓ Testing RAG system initialization...")
try:
    rag_system = rag_module.MedicalRAGSystem(neon_connection, rag_module.CLINICALBERT_AVAILABLE)
    print("✓ RAG system initialized successfully")
except Exception as e:
    print(f"✗ Error initializing RAG system: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test database connection
print("\n✓ Testing database connection...")
try:
    if rag_system.neon_db.connect():
        print("✓ Successfully connected to Neon database")
        
        # Test database query
        print("\n✓ Testing database query...")
        cursor = rag_system.neon_db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM medical_cases;")
        count = cursor.fetchone()[0]
        print(f"✓ Database contains {count} medical cases")
        cursor.close()
    else:
        print("✗ Failed to connect to Neon database")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error connecting to database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("✅ All tests passed! The system is ready to run.")
print("="*50)
print("\nTo start the web server, run:")
print("  python3 load_and_run.py")
