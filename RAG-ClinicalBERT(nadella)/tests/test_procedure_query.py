#!/usr/bin/env python3
"""
Test procedure-type queries against specific case IDs
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
print("Testing Procedure Queries Against Case IDs")
print("="*70)

# First, let's find some cases that mention procedures
cursor = rag_system.neon_db.conn.cursor()

# Find cases with surgical procedures
cursor.execute("""
    SELECT DISTINCT substring(case_id from '^[^_]+_[^_]+_[^_]+') as base_case
    FROM medical_cases
    WHERE content ILIKE '%surgical%' OR content ILIKE '%procedure%' OR content ILIKE '%surgery%'
    LIMIT 5
""")

cases_with_procedures = cursor.fetchall()

print("\n📋 Found cases with procedures:")
for i, (case_id,) in enumerate(cases_with_procedures, 1):
    print(f"  {i}. {case_id}")

# Test with case_0001_mimic (we know it has "Surgical repair of left femoral neck fracture")
print("\n" + "="*70)
print("TEST 1: Query known surgical procedure in case_0001_mimic")
print("="*70)

case_id_1 = "case_0001_mimic.txt"
query_1 = "surgical repair, femoral neck fracture, hip surgery"

print(f"\n📋 Case ID: {case_id_1}")
print(f"❓ Query: {query_1}")

result_1 = rag_system.query_medical_cases(query_1, case_id=case_id_1)

print(f"\n📊 RESULTS:")
print(f"  Confidence: {result_1.confidence:.2f}")
print(f"  Processing Time: {result_1.processing_time:.2f}s")
print(f"  Sources: {', '.join(result_1.sources)}")

print(f"\n📝 ANSWER:")
print("-" * 70)
print(result_1.answer)

# Show what procedures are actually in the case
print(f"\n📄 ACTUAL PROCEDURES IN CASE:")
print("-" * 70)
cursor.execute("""
    SELECT case_id, content
    FROM medical_cases
    WHERE case_id LIKE %s
    ORDER BY case_id
    LIMIT 2
""", (f"{case_id_1.replace('.txt', '')}%",))

for case_id, content in cursor.fetchall():
    # Look for procedure section
    if "procedure" in content.lower() or "surgical" in content.lower():
        # Find the relevant section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'procedure' in line.lower() or 'surgical' in line.lower():
                context_start = max(0, i-1)
                context_end = min(len(lines), i+5)
                print(f"\nFrom {case_id}:")
                print('\n'.join(lines[context_start:context_end]))
                break

# Test 2: Find a case with a specific procedure type
print("\n" + "="*70)
print("TEST 2: Find cases with catheterization procedures")
print("="*70)

query_2 = "cardiac catheterization, angiography, stent placement"

print(f"❓ Query: {query_2}")
print("   (No specific case ID - searching all cases)")

result_2 = rag_system.query_medical_cases(query_2)

print(f"\n📊 RESULTS:")
print(f"  Confidence: {result_2.confidence:.2f}")
print(f"  Processing Time: {result_2.processing_time:.2f}s")
print(f"  Cases Found: {len(result_2.sources)}")

print(f"\n📚 Top 3 Cases with Procedures:")
for i, source in enumerate(result_2.sources[:3], 1):
    print(f"  {i}. {source}")

print(f"\n📝 ANSWER (first 700 chars):")
print("-" * 70)
print(result_2.answer[:700] + "...")

if result_2.relevant_cases:
    print(f"\n📄 FIRST CASE CONTENT PREVIEW:")
    print("-" * 70)
    first_case_content = result_2.relevant_cases[0]['content']
    print(first_case_content[:500] + "...")

# Test 3: Endoscopy procedure
print("\n" + "="*70)
print("TEST 3: Search for endoscopy procedures")
print("="*70)

query_3 = "endoscopy, colonoscopy, biopsy"

print(f"❓ Query: {query_3}")

result_3 = rag_system.query_medical_cases(query_3)

print(f"\n📊 RESULTS:")
print(f"  Confidence: {result_3.confidence:.2f}")
print(f"  Processing Time: {result_3.processing_time:.2f}s")
print(f"  Cases Found: {len(result_3.sources)}")

print(f"\n📚 Top 3 Cases:")
for i, source in enumerate(result_3.sources[:3], 1):
    print(f"  {i}. {source}")

print(f"\n📝 ANSWER (first 700 chars):")
print("-" * 70)
print(result_3.answer[:700] + "...")

# Test 4: Let's pick a random case and query for its procedures
print("\n" + "="*70)
print("TEST 4: Query specific case for any procedures performed")
print("="*70)

# Find a case with procedures mentioned
cursor.execute("""
    SELECT case_id, content
    FROM medical_cases
    WHERE content ILIKE '%Major Surgical or Invasive Procedure%'
    LIMIT 1
""")

random_case = cursor.fetchone()
if random_case:
    case_id_4 = random_case[0]
    content_4 = random_case[1]
    
    # Extract the base case name
    base_case_4 = '_'.join(case_id_4.split('_')[:3]) + '.txt'
    
    print(f"\n📋 Testing Case: {base_case_4}")
    
    # Extract procedure info from content
    if "Major Surgical or Invasive Procedure" in content_4:
        proc_start = content_4.find("Major Surgical or Invasive Procedure")
        proc_section = content_4[proc_start:proc_start+300]
        print(f"\n📄 Procedures mentioned in case:")
        print("-" * 70)
        print(proc_section + "...")
    
    # Query for procedures
    query_4 = "what procedures were performed, surgical procedures, invasive procedures"
    
    print(f"\n❓ Query: {query_4}")
    
    result_4 = rag_system.query_medical_cases(query_4, case_id=base_case_4)
    
    print(f"\n📊 RESULTS:")
    print(f"  Confidence: {result_4.confidence:.2f}")
    print(f"  Processing Time: {result_4.processing_time:.2f}s")
    
    print(f"\n📝 ANSWER:")
    print("-" * 70)
    print(result_4.answer[:800] + "...")

cursor.close()

print("\n" + "="*70)
print("✅ Procedure query testing complete!")
print("="*70)
