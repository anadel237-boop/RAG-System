#!/usr/bin/env python3
"""
Test symptom-based query to find relevant cases
"""
import os
from dotenv import load_dotenv
import optimized_medical_rag_system as rag_module

load_dotenv()

# Initialize system
neon_connection = os.getenv('NEON_CONNECTION_STRING')
print("🔄 Initializing Medical RAG System...\n")

rag_system = rag_module.MedicalRAGSystem(neon_connection, rag_module.CLINICALBERT_AVAILABLE)

if not rag_system.neon_db.connect():
    print("❌ Failed to connect to database")
    exit(1)

print("="*70)
print("Testing Symptom-Based Query")
print("="*70)

# Test with common symptoms
test_queries = [
    {
        "query": "chest pain, shortness of breath, difficulty breathing",
        "description": "Common cardiac/respiratory symptoms"
    },
    {
        "query": "fever, cough, fatigue",
        "description": "Common infection symptoms"
    },
    {
        "query": "abdominal pain, nausea, vomiting",
        "description": "Common GI symptoms"
    }
]

for i, test in enumerate(test_queries, 1):
    query = test["query"]
    description = test["description"]
    
    print(f"\n{'='*70}")
    print(f"TEST {i}: {description}")
    print(f"Query: \"{query}\"")
    print('='*70)
    
    # Run query without specific case ID (semantic search)
    result = rag_system.query_medical_cases(query)
    
    print(f"\n📊 RESULTS:")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Processing Time: {result.processing_time:.2f}s")
    print(f"  Cases Found: {len(result.sources)}")
    
    print(f"\n📚 Top 3 Relevant Cases:")
    for j, source in enumerate(result.sources[:3], 1):
        print(f"  {j}. {source}")
    
    print(f"\n📝 ANSWER:")
    print("-" * 70)
    # Print first 800 characters of answer
    answer_preview = result.answer[:800] + "..." if len(result.answer) > 800 else result.answer
    print(answer_preview)
    
    # Show actual content preview from first case
    if result.relevant_cases:
        first_case = result.relevant_cases[0]
        print(f"\n📄 FIRST CASE PREVIEW ({first_case['case_id']}):")
        print("-" * 70)
        content_preview = first_case['content'][:400] + "..." if len(first_case['content']) > 400 else first_case['content']
        print(content_preview)

print("\n" + "="*70)
print("✅ Symptom testing complete!")
print("="*70)

# Now test with a specific case that we know has symptoms
print("\n" + "="*70)
print("BONUS: Testing specific case with symptom query")
print("="*70)

# Let's pick a random case and see what symptoms it has
cursor = rag_system.neon_db.conn.cursor()
cursor.execute("""
    SELECT case_id, content
    FROM medical_cases
    WHERE case_id LIKE 'case_0050_mimic_chunk_1'
    LIMIT 1
""")

result = cursor.fetchone()
if result:
    case_id_to_test = result[0]
    content = result[1]
    
    print(f"\n📋 Testing Case: {case_id_to_test}")
    print(f"📄 Content Preview:")
    print("-" * 70)
    print(content[:500] + "...")
    
    # Extract chief complaint if present
    if "chief complaint" in content.lower() or "cc:" in content.lower():
        print("\n" + "-" * 70)
        print("Found chief complaint section - extracting...")
        
        # Now query with a symptom from this case
        symptom_query = "abdominal pain"
        print(f"\n🔍 Querying with symptom: \"{symptom_query}\"")
        print(f"   Using case_id: {case_id_to_test.replace('_chunk_1', '.txt')}")
        
        result = rag_system.query_medical_cases(
            symptom_query, 
            case_id=case_id_to_test.replace('_chunk_1', '.txt')
        )
        
        print(f"\n📊 RESULTS:")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Processing Time: {result.processing_time:.2f}s")
        print(f"\n📝 ANSWER:")
        print("-" * 70)
        print(result.answer[:600] + "...")

cursor.close()

print("\n" + "="*70)
