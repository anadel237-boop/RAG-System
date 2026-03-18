import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current dir to path
sys.path.append(os.getcwd())

# Import system
try:
    from optimized_medical_rag_system import MedicalRAGSystem, CLINICALBERT_AVAILABLE
except ImportError as e:
    print(f"ImportError: {e}")
    exit(1)

def test_retrieval():
    load_dotenv()
    
    neon_connection = os.getenv('NEON_CONNECTION_STRING')
    if not neon_connection:
        print("❌ NEON_CONNECTION_STRING not found")
        return

    print(f"ClinicalBERT Available: {CLINICALBERT_AVAILABLE}")
    
    # Initialize system
    rag = MedicalRAGSystem(neon_connection, CLINICALBERT_AVAILABLE)
    
    # Connect
    if not rag.neon_db.connect():
        print("❌ Failed to connect to DB")
        return

    # Test embedding generation
    query = "patient with chest pain"
    embedding = rag.get_embedding(query)
    
    if not embedding:
        print("❌ Failed to generate embedding")
        return
    
    print(f"✅ Generated embedding of length {len(embedding)}")
    
    # Test search
    print(f"🔍 Searching for: '{query}'")
    results = rag.neon_db.search_similar_cases(embedding, limit=5)
    
    if results:
        print(f"✅ Found {len(results)} results")
        for i, res in enumerate(results):
            print(f"  {i+1}. {res.get('case_id')} (Similarity: {res.get('similarity')})")
    else:
        print("❌ No results found")
        
        # Try fallback query manually
        print("🔄 Trying manual fallback query...")
        try:
            rag.neon_db.cursor.execute("SELECT count(*) FROM medical_cases WHERE embedding IS NOT NULL")
            count = rag.neon_db.cursor.fetchone()
            print(f"  Cases with embeddings: {count}")
        except Exception as e:
            print(f"  Error checking count: {e}")

if __name__ == "__main__":
    test_retrieval()
