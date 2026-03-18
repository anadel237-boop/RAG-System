from dotenv import load_dotenv
import os
load_dotenv()
from optimized_medical_rag_system import MedicalRAGSystem, CLINICALBERT_AVAILABLE
rag_system = MedicalRAGSystem(os.getenv('NEON_CONNECTION_STRING'), CLINICALBERT_AVAILABLE)
rag_system.neon_db.connect()
res = rag_system.query_medical_cases("test")
print("Answer starts:", res.answer[:50])
print("Confidence:", res.confidence, type(res.confidence))
print("Processing Time:", res.processing_time, type(res.processing_time))
print("Sources:", res.sources, type(res.sources))
