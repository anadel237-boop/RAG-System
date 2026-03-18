#!/usr/bin/env python3
"""
Medical RAG System with FastAPI - Improved Version
FastAPI-based web interface for medical case analysis using ClinicalBERT
with proper error handling, CORS, and Pydantic models
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime
import re
import hashlib
from collections import defaultdict, Counter
import asyncio
from threading import Lock
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, validator
import tiktoken

# Neon database integration
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import pgvector
    NEON_AVAILABLE = True
except ImportError:
    NEON_AVAILABLE = False
    print("⚠️  Neon dependencies not available. Install with: pip install psycopg2-binary pgvector")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️  FAISS not available. Install with: pip install faiss-cpu")

# ClinicalBERT integration
try:
    from transformers import AutoModel, AutoModelForQuestionAnswering, AutoTokenizer, pipeline
    import torch
    CLINICALBERT_AVAILABLE = True
except ImportError:
    CLINICALBERT_AVAILABLE = False
    print("⚠️  ClinicalBERT not available. Install with: pip install transformers torch")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pydantic models for API validation
class MedicalQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Medical query or question")
    case_id: Optional[str] = Field(None, max_length=255, description="Specific case ID to prioritize")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or just whitespace')
        return v.strip()

class PatientQueryRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=255, description="Patient identifier")
    symptoms: List[str] = Field(..., min_items=1, max_items=20, description="List of symptoms")
    
    @validator('symptoms')
    def validate_symptoms(cls, v):
        if not v or all(not s.strip() for s in v):
            raise ValueError('At least one valid symptom is required')
        return [s.strip() for s in v if s.strip()]

class MedicalQueryResponse(BaseModel):
    success: bool = Field(..., description="Whether the query was successful")
    query: str = Field(..., description="The original query")
    detection_mode: bool = Field(False, description="Whether keyword detection mode was used")
    answer: str = Field(..., description="Generated medical analysis or keyword report")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    sources: List[str] = Field(..., description="Source case IDs used for analysis")
    relevant_cases: int = Field(..., ge=0, description="Number of relevant cases found")
    detections: Optional[List[Dict[str, Any]]] = Field(
        None, description="Per-term detection results when detection mode is active"
    )
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

class PatientQueryResponse(BaseModel):
    success: bool = Field(..., description="Whether the query was successful")
    patient_id: str = Field(..., description="Patient identifier")
    query: str = Field(..., description="Generated query from symptoms")
    answer: str = Field(..., description="Generated medical analysis")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    sources: List[str] = Field(..., description="Source case IDs used for analysis")
    relevant_cases: int = Field(..., ge=0, description="Number of relevant cases found")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

class HealthResponse(BaseModel):
    status: str = Field(..., description="System status")
    clinicalbert_available: bool = Field(..., description="ClinicalBERT availability")
    neon_available: bool = Field(..., description="Neon database availability")
    timestamp: str = Field(..., description="Response timestamp")
    version: str = Field(..., description="API version")

class StatsResponse(BaseModel):
    success: bool = Field(..., description="Whether stats retrieval was successful")
    stats: Dict[str, Any] = Field(..., description="System statistics")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: str = Field(..., description="Error timestamp")

@dataclass
class MedicalCase:
    """Medical case structure"""
    case_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None

@dataclass
class RAGResult:
    """RAG query result"""
    query: str
    relevant_cases: List[Dict[str, Any]]
    answer: str
    confidence: float
    processing_time: float
    sources: List[str]
    detection_mode: bool = False
    detections: Optional[List[Dict[str, Any]]] = None

class NeonRAGDatabase:
    """Neon PostgreSQL database operations for medical RAG"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to Neon database"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # Enable pgvector extension
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            self.conn.commit()
            
            logger.info("✅ Connected to Neon database")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neon: {e}")
            logger.warning("⚠️  Continuing without database connection - some features may be limited")
            return False
    
    def create_tables(self):
        """Create tables for medical RAG system"""
        try:
            # Medical cases table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS medical_cases (
                    id SERIAL PRIMARY KEY,
                    case_id VARCHAR(255) UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Query history table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    case_id VARCHAR(255),
                    answer TEXT,
                    confidence FLOAT,
                    processing_time FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_id ON medical_cases(case_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_metadata ON medical_cases USING GIN(metadata)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_history ON query_history(created_at)")
            
            # Create vector similarity index
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_embedding ON medical_cases USING ivfflat (embedding vector_cosine_ops)")
            
            self.conn.commit()
            logger.info("✅ Created medical RAG tables")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    def insert_medical_case(self, case: MedicalCase):
        """Insert a medical case with embedding"""
        try:
            # Convert embedding to proper vector format
            if case.embedding:
                embedding_str = '[' + ','.join(map(str, case.embedding)) + ']'
            else:
                embedding_str = None
            
            self.cursor.execute("""
                INSERT INTO medical_cases (case_id, content, embedding, metadata)
                VALUES (%s, %s, %s::vector, %s)
                ON CONFLICT (case_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
            """, (
                case.case_id,
                case.content,
                embedding_str,
                json.dumps(case.metadata or {})
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert case {case.case_id}: {e}")
            return False
    
    def search_similar_cases(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Search for similar medical cases using vector similarity"""
        try:
            # Convert embedding to string format for PostgreSQL
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            self.cursor.execute("""
                SELECT case_id, content, metadata,
                       1 - (embedding <=> %s::vector) as similarity
                FROM medical_cases 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (embedding_str, embedding_str, limit))
            
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Failed to search similar cases: {e}")
            return []
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        """Get a specific medical case by ID"""
        try:
            self.cursor.execute("""
                SELECT case_id, content, metadata, created_at
                FROM medical_cases 
                WHERE case_id = %s
            """, (case_id,))
            
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"❌ Failed to get case {case_id}: {e}")
            return None
    
    def save_query_history(self, query: str, case_id: str, answer: str, confidence: float, processing_time: float):
        """Save query to history"""
        try:
            self.cursor.execute("""
                INSERT INTO query_history (query, case_id, answer, confidence, processing_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (query, case_id, answer, confidence, processing_time))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save query history: {e}")
            return False
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        try:
            # Total cases
            self.cursor.execute("SELECT COUNT(*) as total_cases FROM medical_cases")
            total_cases = self.cursor.fetchone()['total_cases']
            
            # Total queries
            self.cursor.execute("SELECT COUNT(*) as total_queries FROM query_history")
            total_queries = self.cursor.fetchone()['total_queries']
            
            # Average confidence
            self.cursor.execute("SELECT AVG(confidence) as avg_confidence FROM query_history WHERE confidence IS NOT NULL")
            avg_confidence = self.cursor.fetchone()['avg_confidence'] or 0
            
            return {
                'total_cases': total_cases,
                'total_queries': total_queries,
                'average_confidence': round(avg_confidence, 2)
            }
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {}

class MedicalRAGSystem:
    """Main Medical RAG System"""
    
    def __init__(self, neon_connection_string: str):
        self.neon_db = NeonRAGDatabase(neon_connection_string)
        
        # Initialize ClinicalBERT
        if CLINICALBERT_AVAILABLE:
            try:
                self.model_name = os.getenv('EMBEDDING_MODEL_NAME', "emilyalsentzer/Bio_ClinicalBERT")
                self.qa_model_name = os.getenv('QA_MODEL_NAME', "dmis-lab/biobert-base-cased-v1.1-squad")

                # Embedding backbone for retrieval
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name)

                # Question-answering head fine-tuned for SQuAD-style QA
                self.qa_tokenizer = AutoTokenizer.from_pretrained(self.qa_model_name)
                self.qa_model = AutoModelForQuestionAnswering.from_pretrained(self.qa_model_name)
                self.qa_pipeline = pipeline(
                    "question-answering",
                    model=self.qa_model,
                    tokenizer=self.qa_tokenizer,
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info("✅ Clinical embeddings and QA pipeline initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize ClinicalBERT: {e}")
                self.model = None
                self.tokenizer = None
                self.qa_model = None
                self.qa_tokenizer = None
                self.qa_pipeline = None
        else:
            self.model = None
            self.tokenizer = None
            self.qa_model = None
            self.qa_tokenizer = None
            self.qa_pipeline = None
        
        # RAG configuration
        self.retrieval_top_k = int(os.getenv('RETRIEVAL_TOP_K', 5))
        self.context_window = int(os.getenv('CONTEXT_WINDOW', 4000))
        self.max_tokens = int(os.getenv('MAX_TOKENS', 2000))
        self.temperature = float(os.getenv('TEMPERATURE', 0.1))
        self.enable_local_fallback = os.getenv('ENABLE_LOCAL_FALLBACK', 'true').lower() == 'true'
        self.local_cases_dir = Path(os.getenv('LOCAL_CASES_DIR', 'data'))
        self._local_index_lock = Lock()
        self._local_index_data = None
        self._local_case_map: Dict[str, Dict[str, Any]] = {}
        self._local_index_failed = False
        keywords_env = os.getenv('DETECTION_KEYWORDS', '')
        self.default_keywords = [k.strip() for k in keywords_env.split(',') if k.strip()]
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get ClinicalBERT embedding for text"""
        if not self.model or not self.tokenizer:
            logger.warning("⚠️  ClinicalBERT not available")
            return None
        
        try:
            # Tokenize and encode text
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
            
            # Get model outputs
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use mean pooling of last hidden states
                embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"❌ Failed to get embedding: {e}")
            return None
    
    def _build_local_index(self) -> Optional[Dict[str, Any]]:
        """Build FAISS-backed fallback index using local case files"""
        if not self.enable_local_fallback or not FAISS_AVAILABLE:
            return None
        if self._local_index_failed:
            return None
        
        with self._local_index_lock:
            if self._local_index_data is not None:
                return self._local_index_data
            
            if not self.local_cases_dir.exists():
                logger.warning(f"⚠️  Local cases directory not found: {self.local_cases_dir}")
                self._local_index_failed = True
                return None
            
            case_files = sorted(self.local_cases_dir.glob("case_*.txt"))
            if not case_files:
                logger.warning(f"⚠️  No local case files found in {self.local_cases_dir}")
                self._local_index_failed = True
                return None
            
            embeddings = []
            cases = []
            case_map: Dict[str, Dict[str, Any]] = {}
            
            for path in case_files:
                try:
                    content = path.read_text(encoding='utf-8')
                except Exception as read_err:
                    logger.warning(f"⚠️  Failed to read {path}: {read_err}")
                    continue
                
                if not content.strip():
                    continue
                
                embedding = self.get_embedding(content)
                if not embedding:
                    continue
                
                embedding_array = np.array(embedding, dtype='float32')
                embeddings.append(embedding_array)
                
                case_dict = {
                    'case_id': path.name,
                    'content': content,
                    'metadata': {
                        'source': 'local_fallback',
                        'file_path': str(path)
                    }
                }
                cases.append(case_dict)
                case_map[path.name] = case_dict
            
            if not embeddings:
                logger.warning("⚠️  Unable to build local index - no embeddings generated")
                self._local_index_failed = True
                return None
            
            embedding_matrix = np.stack(embeddings).astype('float32')
            faiss.normalize_L2(embedding_matrix)
            index = faiss.IndexFlatIP(embedding_matrix.shape[1])
            index.add(embedding_matrix)
            
            self._local_index_data = {
                'index': index,
                'matrix': embedding_matrix,
                'cases': cases
            }
            self._local_case_map = case_map
            
            logger.info(f"✅ Local FAISS index built with {len(cases)} cases")
            return self._local_index_data
    
    def search_local_cases(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Search local FAISS index for similar cases"""
        index_data = self._build_local_index()
        if not index_data:
            return []
        
        index = index_data['index']
        if index.ntotal == 0:
            return []
        
        top_k = min(limit, index.ntotal)
        query_vector = np.array([query_embedding], dtype='float32')
        faiss.normalize_L2(query_vector)
        
        distances, indices = index.search(query_vector, top_k)
        cases = index_data['cases']
        
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(cases):
                continue
            case_info = cases[idx].copy()
            case_info['similarity'] = float(score)
            results.append(case_info)
        
        return results
    
    def get_local_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a local fallback case by ID"""
        index_data = self._build_local_index()
        if not index_data:
            return None
        
        case = self._local_case_map.get(case_id)
        return case.copy() if case else None
    
    def extract_keywords(self, query: str) -> List[str]:
        """Extract potential keyword terms from the query text"""
        if not query:
            return []
        
        parts = [segment.strip() for segment in re.split(r'[,\n;/]+', query) if segment.strip()]
        if parts:
            return parts
        
        # Fallback: if the query is short, treat it as a single keyword phrase
        words = query.strip().split()
        if 0 < len(words) <= 4:
            return [query.strip()]
        
        return []
    
    def detect_keywords_in_case(self, case: Dict[str, Any], keywords: List[str]) -> List[Dict[str, Any]]:
        """Detect keywords within a specific medical case"""
        text = case.get('content', '')
        if not text:
            return []
        
        lower_text = text.lower()
        detections = []
        
        for term in keywords:
            normalized_term = term.strip()
            if not normalized_term:
                continue
            term_lower = normalized_term.lower()
            index = lower_text.find(term_lower)
            present = index != -1
            snippet = ""
            if present:
                start = max(0, index - 80)
                end = min(len(text), index + len(normalized_term) + 80)
                snippet = text[start:end].replace('\n', ' ').strip()
            
            detections.append({
                'term': normalized_term,
                'present': present,
                'confidence': 1.0 if present else 0.0,
                'snippet': snippet
            })
        
        return detections
    
    def generate_answer(self, query: str, context_cases: List[Dict]) -> Tuple[str, float]:
        """Generate answer using ClinicalBERT with retrieved context"""
        if not self.qa_pipeline:
            return "❌ ClinicalBERT not available", 0.0
        
        try:
            # Prepare context
            context_text = ""
            for i, case in enumerate(context_cases, 1):
                context_text += f"Case {i} ({case['case_id']}):\n{case['content'][:500]}...\n\n"
            
            # Truncate context if too long
            if len(context_text) > self.context_window:
                context_text = context_text[:self.context_window] + "..."
            
            # Use ClinicalBERT for question answering
            result = self.qa_pipeline(question=query, context=context_text)
            
            # Extract answer and confidence
            answer = result['answer']
            confidence = result['score']
            
            # Format the response with additional analysis
            formatted_answer = f"""Based on the medical cases provided, here is my analysis:

**Answer:** {answer}

**Key Findings:**
- Analysis based on {len(context_cases)} relevant medical cases
- ClinicalBERT confidence score: {confidence:.2f}

**Medical Context:**
The analysis is derived from similar medical cases in the database, providing evidence-based insights for the query.

**Note:** This is an AI-generated analysis based on available medical case data. Always consult with qualified medical professionals for clinical decisions."""
            
            return formatted_answer, confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to generate answer: {e}")
            return f"❌ Error generating answer: {e}", 0.0
    
    def query_medical_cases(self, query: str, case_id: Optional[str] = None) -> RAGResult:
        """Query medical cases using RAG"""
        start_time = datetime.now()
        detection_case = None
        detection_terms: List[str] = []
        try:
            if case_id:
                detection_case = self.neon_db.get_case_by_id(case_id)
                if not detection_case and self.enable_local_fallback:
                    detection_case = self.get_local_case_by_id(case_id)
                
                detection_terms = self.extract_keywords(query)
                if not detection_terms and self.default_keywords:
                    detection_terms = self.default_keywords
                
                if detection_case and detection_terms:
                    detections = self.detect_keywords_in_case(detection_case, detection_terms)
                    if detections:
                        yes_count = sum(1 for d in detections if d['present'])
                        confidence = yes_count / len(detections)
                        processing_time = (datetime.now() - start_time).total_seconds()
                        status_lines = [f"Keyword detection for case {case_id}:"]
                        for det in detections:
                            status = "YES" if det['present'] else "NO"
                            status_lines.append(f"- {det['term']}: {status}")
                        answer = "\n".join(status_lines)
                        sources = [case_id]
                        relevant_cases = [detection_case]
                        
                        try:
                            self.neon_db.save_query_history(
                                query,
                                case_id,
                                answer,
                                confidence,
                                processing_time
                            )
                        except Exception as history_error:
                            logger.debug(f"History logging skipped: {history_error}")
                        
                        return RAGResult(
                            query=query,
                            relevant_cases=relevant_cases,
                            answer=answer,
                            confidence=confidence,
                            processing_time=processing_time,
                            sources=sources,
                            detection_mode=True,
                            detections=detections
                        )
            
            # Get embedding for query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return RAGResult(
                    query=query,
                    relevant_cases=[],
                    answer="❌ Failed to get query embedding",
                    confidence=0.0,
                    processing_time=0.0,
                    sources=[]
                )
            
            # Search for similar cases
            similar_cases = self.neon_db.search_similar_cases(query_embedding, limit=self.retrieval_top_k)
            if not similar_cases:
                local_cases = self.search_local_cases(query_embedding, limit=self.retrieval_top_k)
                if local_cases:
                    logger.info("ℹ️  Using local FAISS fallback for retrieval")
                    similar_cases = local_cases
            
            if not similar_cases:
                return RAGResult(
                    query=query,
                    relevant_cases=[],
                    answer="❌ No relevant cases found",
                    confidence=0.0,
                    processing_time=0.0,
                    sources=[]
                )
            
            # If specific case requested, prioritize it
            if case_id:
                case = self.neon_db.get_case_by_id(case_id)
                if not case and self.enable_local_fallback:
                    case = self.get_local_case_by_id(case_id)
                if case:
                    similar_cases = [c for c in similar_cases if c.get('case_id') != case_id]
                    similar_cases.insert(0, case)
            
            # Generate answer
            answer, confidence = self.generate_answer(query, similar_cases)
            
            # Prepare sources
            sources = [case['case_id'] for case in similar_cases]
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Save to history
            self.neon_db.save_query_history(query, case_id or "general", answer, confidence, processing_time)
            
            return RAGResult(
                query=query,
                relevant_cases=similar_cases,
                answer=answer,
                confidence=confidence,
                processing_time=processing_time,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to query medical cases: {e}")
            return RAGResult(
                query=query,
                relevant_cases=[],
                answer=f"❌ Error: {e}",
                confidence=0.0,
                processing_time=0.0,
                sources=[]
            )

# Global RAG system instance
rag_system = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global rag_system
    
    # Startup
    logger.info("🚀 Starting Medical RAG System with FastAPI")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    neon_connection = os.getenv('NEON_CONNECTION_STRING')
    
    if not neon_connection:
        logger.error("❌ NEON_CONNECTION_STRING not found in environment")
        yield
        return
    
    # Initialize RAG system
    rag_system = MedicalRAGSystem(neon_connection)
    
    # Try to connect to database
    rag_system.neon_db.connect()
    
    logger.info("✅ Medical RAG System with FastAPI started")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Medical RAG System")

# FastAPI app with improved configuration
app = FastAPI(
    title="Medical RAG System API",
    description="""
    A comprehensive Retrieval-Augmented Generation (RAG) system for medical case analysis using ClinicalBERT.
    
    ## Features
    - **ClinicalBERT Integration**: Medical-specific language model for analysis
    - **Vector Search**: Semantic similarity search across medical cases
    - **Neon Database**: PostgreSQL with pgvector for efficient storage
    - **RESTful API**: Clean, documented API endpoints
    - **Error Handling**: Comprehensive error responses
    - **CORS Support**: Cross-origin resource sharing enabled
    
    ## Authentication
    No authentication required for this demo version.
    """,
    version="2.0.0",
    contact={
        "name": "Medical RAG System",
        "email": "support@medicalrag.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# CORS middleware with comprehensive configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # In production, specify actual hosts
)

# Custom exception handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error=f"Validation error: {exc.errors()}",
            error_code="VALIDATION_ERROR",
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            timestamp=datetime.now().isoformat()
        ).dict()
    )

# HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medical RAG System - FastAPI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 40px;
            font-size: 2.5em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .form-group { margin-bottom: 25px; }
        label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: #34495e;
            font-size: 1.1em;
        }
        input, textarea, select { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #e1e8ed; 
            border-radius: 10px; 
            font-size: 16px;
            transition: all 0.3s ease;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        textarea { 
            height: 120px; 
            resize: vertical; 
            font-family: inherit;
        }
        button { 
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            font-size: 18px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .result { 
            margin-top: 30px; 
            padding: 25px; 
            background: #f8f9fa; 
            border-radius: 15px; 
            border-left: 5px solid #667eea;
        }
        .confidence { 
            color: #27ae60; 
            font-weight: bold; 
            font-size: 1.1em;
        }
        .processing-time { 
            color: #7f8c8d; 
            font-size: 14px;
        }
        .sources { margin-top: 20px; }
        .source { 
            background: #e8f4f8; 
            padding: 10px 15px; 
            margin: 8px 0; 
            border-radius: 8px; 
            font-size: 14px;
            border-left: 3px solid #3498db;
        }
        .loading { 
            display: none; 
            color: #667eea; 
            text-align: center;
            font-size: 1.1em;
            margin: 20px 0;
        }
        .error { 
            color: #e74c3c; 
            background: #fdf2f2; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 15px 0;
            border-left: 5px solid #e74c3c;
        }
        .success { 
            color: #27ae60; 
            background: #f0f9f0; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 15px 0;
            border-left: 5px solid #27ae60;
        }
        .api-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .api-info a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .api-info a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Medical RAG System</h1>
        
        <div class="api-info">
            <p><strong>API Documentation:</strong> <a href="/docs" target="_blank">Interactive Docs</a> | 
            <strong>Health Check:</strong> <a href="/api/health" target="_blank">System Status</a></p>
        </div>
        
        <form id="queryForm">
            <div class="form-group">
                <label for="query">Medical Query:</label>
                <textarea id="query" name="query" placeholder="Enter your medical question or symptoms..." required></textarea>
            </div>
            
            <div class="form-group">
                <label for="case_id">Specific Case ID (optional):</label>
                <input type="text" id="case_id" name="case_id" placeholder="e.g., case_0001_mimic.txt">
            </div>
            
            <button type="submit" id="submitBtn">🔍 Query Medical Cases</button>
            <div class="loading" id="loading">⏳ Processing your request...</div>
        </form>
        
        <div id="result" class="result" style="display: none;">
            <h3>📊 Analysis Results</h3>
            <div id="answer"></div>
            <div id="metadata"></div>
            <div id="sources" class="sources"></div>
        </div>
        
        <div id="error" class="error" style="display: none;"></div>
        <div id="success" class="success" style="display: none;"></div>
    </div>

    <script>
        document.getElementById('queryForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const query = document.getElementById('query').value;
            const caseId = document.getElementById('case_id').value;
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            
            // Show loading, hide previous results
            submitBtn.disabled = true;
            loading.style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            document.getElementById('success').style.display = 'none';
            
            try {
                const response = await fetch('/api/medical_query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, case_id: caseId || null })
                });
                
                const result = await response.json();
                
                loading.style.display = 'none';
                submitBtn.disabled = false;
                
                if (result.success) {
                    document.getElementById('answer').innerHTML = result.answer.replace(/\\n/g, '<br>');
                    document.getElementById('metadata').innerHTML = `
                        <p><span class="confidence">Confidence: ${(result.confidence * 100).toFixed(1)}%</span> | 
                        <span class="processing-time">Processing Time: ${result.processing_time.toFixed(2)}s</span></p>
                    `;
                    
                    let sourcesHtml = '<h4>📚 Sources:</h4>';
                    result.sources.forEach(source => {
                        sourcesHtml += `<div class="source">${source}</div>`;
                    });
                    document.getElementById('sources').innerHTML = sourcesHtml;
                    
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('success').textContent = `✅ Query successful! Found ${result.relevant_cases} relevant cases.`;
                    document.getElementById('success').style.display = 'block';
                } else {
                    document.getElementById('error').textContent = 'Error: ' + (result.error || 'Unknown error');
                    document.getElementById('error').style.display = 'block';
                }
            } catch (error) {
                loading.style.display = 'none';
                submitBtn.disabled = false;
                document.getElementById('error').textContent = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, tags=["Web Interface"])
async def index():
    """Main web interface"""
    return HTML_TEMPLATE

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        clinicalbert_available=CLINICALBERT_AVAILABLE,
        neon_available=NEON_AVAILABLE,
        timestamp=datetime.now().isoformat(),
        version="2.0.0"
    )

@app.post("/api/medical_query", response_model=MedicalQueryResponse, tags=["Medical Analysis"])
async def medical_query(query_data: MedicalQueryRequest):
    """Query medical cases using RAG"""
    try:
        if not rag_system:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG system not initialized"
            )
        
        result = rag_system.query_medical_cases(query_data.query, query_data.case_id)
        
        return MedicalQueryResponse(
            success=True,
            query=result.query,
            detection_mode=result.detection_mode,
            answer=result.answer,
            confidence=result.confidence,
            processing_time=result.processing_time,
            sources=result.sources,
            relevant_cases=len(result.relevant_cases),
            detections=result.detections
        )
    except Exception as e:
        logger.error(f"❌ Medical query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )

@app.post("/api/patient_query", response_model=PatientQueryResponse, tags=["Medical Analysis"])
async def patient_query(patient_data: PatientQueryRequest):
    """Patient-specific query"""
    try:
        if not rag_system:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG system not initialized"
            )
        
        # Create query from symptoms
        query = f"Patient {patient_data.patient_id} with symptoms: {', '.join(patient_data.symptoms)}"
        
        result = rag_system.query_medical_cases(query, patient_data.patient_id)
        
        return PatientQueryResponse(
            success=True,
            patient_id=patient_data.patient_id,
            query=result.query,
            answer=result.answer,
            confidence=result.confidence,
            processing_time=result.processing_time,
            sources=result.sources,
            relevant_cases=len(result.relevant_cases)
        )
    except Exception as e:
        logger.error(f"❌ Patient query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Patient query processing failed: {str(e)}"
        )

@app.get("/api/system_stats", response_model=StatsResponse, tags=["System"])
async def system_stats():
    """Get system statistics"""
    try:
        if not rag_system or not rag_system.neon_db.conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not connected"
            )
        
        stats = rag_system.neon_db.get_system_stats()
        return StatsResponse(success=True, stats=stats)
    except Exception as e:
        logger.error(f"❌ System stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system statistics: {str(e)}"
        )

@app.get("/api/docs", tags=["Documentation"])
async def api_docs_redirect():
    """Redirect to FastAPI docs"""
    return {"message": "Visit /docs for interactive API documentation", "docs_url": "/docs"}

if __name__ == "__main__":
    import uvicorn
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv('FLASK_PORT', 5557))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    logger.info(f"🌐 Starting Medical RAG System with FastAPI on {host}:{port}")
    logger.info(f"📱 Access at: http://localhost:{port}")
    logger.info(f"📚 API docs at: http://localhost:{port}/docs")
    
    uvicorn.run(
        app, 
        host=host, 
        port=port, 
        log_level="info",
        access_log=True
    )
