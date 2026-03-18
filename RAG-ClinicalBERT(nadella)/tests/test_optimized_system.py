#!/usr/bin/env python3
"""
Test script for the optimized medical RAG system
Tests with the specific case and query provided by the user
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_system():
    """Test the optimized system with the user's specific case"""
    
    print("🧪 Testing Optimized Medical RAG System")
    print("=" * 50)
    
    # Check if optimized system exists
    if not Path("optimized_medical_rag_system.py").exists():
        print("❌ optimized_medical_rag_system.py not found")
        return False
    
    # Check environment
    if not os.getenv('NEON_CONNECTION_STRING'):
        print("❌ NEON_CONNECTION_STRING not found")
        return False
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found")
        return False
    
    print("✅ Environment variables found")
    
    # Test case file
    case_file = Path("data/case_0001_mimic.txt")
    if not case_file.exists():
        print(f"❌ Test case file not found: {case_file}")
        return False
    
    print(f"✅ Test case file found: {case_file}")
    
    # Test query
    test_query = "schizophrenia, Parkinson's disease, Crohn's disease"
    case_id = "case_0001_mimic.txt"
    
    print(f"📝 Test query: {test_query}")
    print(f"📁 Test case ID: {case_id}")
    
    try:
        # Import the optimized system
        from optimized_medical_rag_system import MedicalRAGSystem
        
        # Initialize system
        print("🔄 Initializing RAG system...")
        rag_system = MedicalRAGSystem(
            os.getenv('NEON_CONNECTION_STRING'),
            os.getenv('OPENAI_API_KEY')
        )
        
        # Connect to database
        if not rag_system.neon_db.connect():
            print("❌ Failed to connect to database")
            return False
        
        print("✅ Connected to database")
        
        # Process cases incrementally (this will be fast if already processed)
        print("🔄 Processing cases incrementally...")
        cases_dir = "data"
        if Path(cases_dir).exists():
            rag_system.process_medical_cases_incremental(cases_dir)
            print("✅ Case processing completed")
        
        # Test query
        print("🔍 Testing query...")
        result = rag_system.query_medical_cases(test_query, case_id)
        
        print("\n📊 Query Results:")
        print(f"Query: {result.query}")
        print(f"Answer: {result.answer[:200]}...")
        print(f"Confidence: {result.confidence}")
        print(f"Processing Time: {result.processing_time}s")
        print(f"Sources: {result.sources}")
        
        if result.answer and not result.answer.startswith("❌"):
            print("✅ Query successful!")
            return True
        else:
            print("❌ Query failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Medical RAG System Test")
    print("Testing with case_0001_mimic.txt and query about schizophrenia, Parkinson's, Crohn's")
    print()
    
    success = test_system()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("You can now run the optimized system with:")
        print("python run_optimized_system.py")
    else:
        print("\n❌ Test failed. Please check your configuration.")

if __name__ == "__main__":
    main()

