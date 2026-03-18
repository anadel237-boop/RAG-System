#!/usr/bin/env python3
"""
Debug vector search issues
"""
import os
from dotenv import load_dotenv
import optimized_medical_rag_system as rag_module
import numpy as np

load_dotenv()

# Initialize system
neon_connection = os.getenv('NEON_CONNECTION_STRING')
print("🔄 Initializing system...\n")

rag_system = rag_module.MedicalRAGSystem(neon_connection, rag_module.CLINICALBERT_AVAILABLE)

if not rag_system.neon_db.connect():
    print("❌ Failed to connect to database")
    exit(1)

# Test different queries
test_queries = [
    "diabetes symptoms",
    "chest pain",
    "hypertension treatment",
]

print("="*60)
print("Debug: Vector Search Analysis")
print("="*60)

for query in test_queries:
    print(f"\n🔍 Testing query: '{query}'")
    print("-" * 60)
    
    # Get embedding
    embedding = rag_system.get_embedding(query)
    if not embedding:
        print("❌ Failed to get embedding")
        continue
    
    print(f"✓ Embedding generated: dimension={len(embedding)}")
    print(f"  - Min value: {min(embedding):.4f}")
    print(f"  - Max value: {max(embedding):.4f}")
    print(f"  - Mean value: {np.mean(embedding):.4f}")
    print(f"  - Std dev: {np.std(embedding):.4f}")
    
    # Try search
    results = rag_system.neon_db.search_similar_cases(embedding, limit=5)
    print(f"\n  Results found: {len(results)}")
    
    if results:
        for i, result in enumerate(results[:3], 1):
            similarity = result.get('similarity', 'N/A')
            distance = result.get('distance', 'N/A')
            case_id = result.get('case_id', 'Unknown')
            content_preview = result.get('content', '')[:100]
            print(f"  {i}. {case_id}")
            print(f"     Similarity: {similarity}, Distance: {distance}")
            print(f"     Preview: {content_preview}...")
    else:
        print("  ⚠️ No results returned")

print("\n" + "="*60)

# Check database stats
cursor = rag_system.neon_db.conn.cursor()

# Check total cases
cursor.execute("SELECT COUNT(*) FROM medical_cases")
total = cursor.fetchone()[0]
print(f"Total cases in DB: {total}")

# Check cases with embeddings
cursor.execute("SELECT COUNT(*) FROM medical_cases WHERE embedding IS NOT NULL")
with_embeddings = cursor.fetchone()[0]
print(f"Cases with embeddings: {with_embeddings}")

# Sample a case embedding
cursor.execute("SELECT case_id, array_length(embedding, 1) as dim FROM medical_cases WHERE embedding IS NOT NULL LIMIT 1")
sample = cursor.fetchone()
if sample:
    print(f"Sample case: {sample[0]}, embedding dimension: {sample[1]}")

cursor.close()
print("="*60)
