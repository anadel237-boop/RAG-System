#!/usr/bin/env python3
"""
Fix the vector index issue by rebuilding it properly
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

conn = psycopg2.connect(os.getenv('NEON_CONNECTION_STRING'))
conn.autocommit = True
cursor = conn.cursor()

print("="*60)
print("Fixing Vector Index")
print("="*60)

# Drop the old index
print("\n🔄 Dropping old ivfflat index...")
try:
    cursor.execute("DROP INDEX IF EXISTS idx_cases_embedding")
    print("✅ Old index dropped")
except Exception as e:
    print(f"⚠️  Error dropping index: {e}")

# Create a proper HNSW index instead (better for < 1M vectors)
# HNSW is more reliable than IVFFlat for smaller datasets
print("\n🔄 Creating HNSW index (better for datasets < 1M vectors)...")
try:
    cursor.execute("""
        CREATE INDEX idx_cases_embedding ON medical_cases 
        USING hnsw (embedding vector_cosine_ops)
    """)
    print("✅ HNSW index created successfully")
except Exception as e:
    print(f"❌ Error creating HNSW index: {e}")
    print("\n🔄 Trying IVFFlat index with proper configuration...")
    try:
        # For IVFFlat, we need to set the lists parameter
        # Rule of thumb: lists = rows / 1000, but min 10
        cursor.execute("SELECT COUNT(*) FROM medical_cases WHERE embedding IS NOT NULL")
        count = cursor.fetchone()[0]
        lists = max(10, count // 100)  # More conservative
        
        print(f"   Using {lists} lists for {count} vectors")
        
        cursor.execute(f"""
            CREATE INDEX idx_cases_embedding ON medical_cases 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {lists})
        """)
        print("✅ IVFFlat index created with proper configuration")
    except Exception as e2:
        print(f"❌ Error creating IVFFlat index: {e2}")

# Test the index
print("\n" + "="*60)
print("Testing Vector Search")
print("="*60)

test_vector = '[' + ','.join(['0.1'] * 768) + ']'

try:
    cursor.execute("""
        SELECT case_id, 
               LEFT(content, 80) as preview,
               embedding <=> %s::vector as distance
        FROM medical_cases
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT 5
    """, (test_vector, test_vector))
    
    results = cursor.fetchall()
    print(f"\n✅ Search successful! Found {len(results)} results")
    
    for i, row in enumerate(results, 1):
        case_id, preview, distance = row
        print(f"{i}. {case_id} (distance: {distance:.4f})")
        print(f"   {preview}...")
        
except Exception as e:
    print(f"\n❌ Search test failed: {e}")
    import traceback
    traceback.print_exc()

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ Vector index fix complete!")
print("="*60)
