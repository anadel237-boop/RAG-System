#!/usr/bin/env python3
"""
Test query functionality with improved answer generation
"""
import os
from dotenv import load_dotenv
import optimized_medical_rag_system as rag_module

# Load environment variables
load_dotenv()

# Initialize system
neon_connection = os.getenv('NEON_CONNECTION_STRING')
print("🔄 Initializing Medical RAG System...\n")

rag_system = rag_module.MedicalRAGSystem(neon_connection, rag_module.CLINICALBERT_AVAILABLE)

# Connect to database
if not rag_system.neon_db.connect():
    print("❌ Failed to connect to database")
    exit(1)

# Test queries
test_queries = [
    "What are common symptoms of diabetes?",
    "Patient with chest pain and shortness of breath",
    "What treatments are used for hypertension?",
]

print("="*60)
print("Testing Query System with Enhanced Answer Generation")
print("="*60)

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*60}")
    print(f"Test Query {i}: {query}")
    print('='*60)
    
    result = rag_system.query_medical_cases(query)
    
    print(f"\n📊 Results:")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Sources: {', '.join(result.sources[:3])}...")
    print(f"\n📝 Answer:\n{result.answer}\n")

print("\n" + "="*60)
print("✅ Query testing complete!")
print("="*60)
