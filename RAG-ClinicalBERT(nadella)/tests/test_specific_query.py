#!/usr/bin/env python3
"""
Test specific query with case_0001_mimic.txt
"""
import os
from dotenv import load_dotenv
import optimized_medical_rag_system as rag_module

load_dotenv()

# Initialize system
neon_connection = os.getenv('NEON_CONNECTION_STRING')
print("🔄 Initializing Medical RAG System...\n")

rag_system = rag_module.MedicalRAGSystem(neon_connection, rag_module.CLINICALBERT_AVAILABLE)

# Connect to database
if not rag_system.neon_db.connect():
    print("❌ Failed to connect to database")
    exit(1)

print("="*70)
print("Testing Specific Case and Query")
print("="*70)

# Test parameters
case_id = "case_0001_mimic.txt"
query = "schizophrenia,chrohn's disease,parkinsons disease"

print(f"\n📋 Case ID: {case_id}")
print(f"❓ Query: {query}")
print("\n" + "="*70)

# Run the query
result = rag_system.query_medical_cases(query, case_id=case_id)

print(f"\n📊 RESULTS:")
print("="*70)
print(f"Confidence: {result.confidence:.2f}")
print(f"Processing Time: {result.processing_time:.2f}s")
print(f"Number of sources: {len(result.sources)}")
print(f"\n📚 Sources:")
for i, source in enumerate(result.sources, 1):
    print(f"  {i}. {source}")

print(f"\n📝 ANSWER:")
print("="*70)
print(result.answer)
print("\n" + "="*70)

# Also show the actual case content for reference
print("\n📄 CASE CONTENT PREVIEW:")
print("="*70)

cursor = rag_system.neon_db.conn.cursor()
cursor.execute("""
    SELECT case_id, LEFT(content, 500) as preview
    FROM medical_cases
    WHERE case_id LIKE %s
    ORDER BY case_id
    LIMIT 3
""", (f"{case_id.replace('.txt', '')}%",))

chunks = cursor.fetchall()
if chunks:
    for i, (cid, preview) in enumerate(chunks, 1):
        print(f"\n{i}. {cid}")
        print(f"{preview}...")
        print("-" * 70)
else:
    print("⚠️  Case not found in database")

cursor.close()
print("\n" + "="*70)
print("✅ Test complete!")
print("="*70)
