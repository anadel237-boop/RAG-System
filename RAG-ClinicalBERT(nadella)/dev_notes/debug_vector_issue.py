#!/usr/bin/env python3
"""
Debug vector search - check if vectors are being stored and retrieved correctly
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

conn = psycopg2.connect(os.getenv('NEON_CONNECTION_STRING'))
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("="*60)
print("Vector Search Debugging")
print("="*60)

# Check if vector extension is enabled
cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
result = cursor.fetchone()
if result:
    print(f"\n✅ pgvector extension: {result['extname']} v{result['extversion']}")
else:
    print("\n❌ pgvector extension not found!")

# Check table structure
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'medical_cases' AND column_name = 'embedding'
""")
result = cursor.fetchone()
if result:
    print(f"✅ Embedding column type: {result['data_type']}")
else:
    print("❌ Embedding column not found!")

# Check if we have any embeddings
cursor.execute("SELECT COUNT(*) as count FROM medical_cases WHERE embedding IS NOT NULL")
count = cursor.fetchone()['count']
print(f"✅ Cases with embeddings: {count}")

# Get a sample embedding to see its format
cursor.execute("""
    SELECT case_id, 
           embedding::text as emb_text,
           length(embedding::text) as emb_length
    FROM medical_cases 
    WHERE embedding IS NOT NULL 
    LIMIT 1
""")
sample = cursor.fetchone()
if sample:
    print(f"\n📝 Sample case: {sample['case_id']}")
    print(f"   Embedding text length: {sample['emb_length']}")
    print(f"   First 100 chars: {sample['emb_text'][:100]}")

# Try a simple vector query to see what happens
print("\n" + "="*60)
print("Testing Vector Query")
print("="*60)

# Create a test query vector (all zeros for simplicity)
test_vector = '[' + ','.join(['0'] * 768) + ']'
print(f"\n🔬 Test vector: dimension=768, all zeros")

try:
    cursor.execute("""
        SELECT case_id,
               LEFT(content, 100) as content_preview,
               embedding <=> %s::vector as distance
        FROM medical_cases
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT 3
    """, (test_vector, test_vector))
    
    results = cursor.fetchall()
    print(f"\n✅ Query successful! Found {len(results)} results")
    
    for i, row in enumerate(results, 1):
        print(f"\n{i}. {row['case_id']}")
        print(f"   Distance: {row['distance']}")
        print(f"   Preview: {row['content_preview']}...")
        
except Exception as e:
    print(f"\n❌ Query failed: {e}")
    import traceback
    traceback.print_exc()

# Check if index exists
print("\n" + "="*60)
print("Checking Indexes")
print("="*60)

cursor.execute("""
    SELECT indexname, indexdef 
    FROM pg_indexes 
    WHERE tablename = 'medical_cases' AND indexname LIKE '%embedding%'
""")
indexes = cursor.fetchall()
if indexes:
    for idx in indexes:
        print(f"\n✅ Index: {idx['indexname']}")
        print(f"   Definition: {idx['indexdef']}")
else:
    print("\n⚠️ No vector indexes found on embedding column")

cursor.close()
conn.close()

print("\n" + "="*60)
