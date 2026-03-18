#!/usr/bin/env python3
"""
Optimized Medical RAG System with Neon Vector Database
- Implements caching to avoid reprocessing cases
- Better error handling for web interface
- Incremental processing with resume capability
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime
import re
import hashlib
from collections import defaultdict, Counter
import asyncio
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import tiktoken
import pickle
import sqlite3

# Use a pipeline as a high-level helper
from transformers import pipeline

# Note: ClinicalBERT pipeline will be initialized later in the MedicalRAGSystem class
# Neon database integration
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import pgvector
    NEON_AVAILABLE = True
except ImportError:
    NEON_AVAILABLE = False
    print("⚠️  Neon dependencies not available. Install with: pip install psycopg2-binary pgvector")

# ClinicalBERT integration
try:
    from transformers import AutoModel, AutoTokenizer, pipeline
    import torch
    CLINICALBERT_AVAILABLE = True
except ImportError as e:
    CLINICALBERT_AVAILABLE = False
    print(f"⚠️  ClinicalBERT not available: {e}")
    print("⚠️  Install with: pip install transformers torch")
except Exception as e:
    CLINICALBERT_AVAILABLE = False
    print(f"⚠️  ClinicalBERT initialization error: {e}")
    print("⚠️  Continuing without ClinicalBERT - some features may be limited")

# OpenAI integration (for answer generation/synthesis)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not available. Install with: pip install openai")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class ProcessingCache:
    """Local cache to track processing progress - thread-safe"""
    
    def __init__(self, cache_file: str = "processing_cache.db"):
        self.cache_file = cache_file
        self._init_cache()
    
    def _get_connection(self):
        """Get a thread-safe SQLite connection"""
        conn = sqlite3.connect(self.cache_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_cache(self):
        """Initialize cache tables"""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    processed_at TIMESTAMP,
                    chunks_count INTEGER,
                    status TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_stats (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def get_file_hash(self, file_path: str) -> str:
        """Get file hash for change detection"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def is_file_processed(self, file_path: str) -> bool:
        """Check if file has been processed"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT file_hash FROM processed_files WHERE file_path = ?", 
                (file_path,)
            )
            result = cursor.fetchone()
            if not result:
                return False
            
            current_hash = self.get_file_hash(file_path)
            return result[0] == current_hash and current_hash != ""
        finally:
            conn.close()
    
    def mark_file_processed(self, file_path: str, chunks_count: int):
        """Mark file as processed"""
        file_hash = self.get_file_hash(file_path)
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO processed_files 
                (file_path, file_hash, processed_at, chunks_count, status)
                VALUES (?, ?, ?, ?, ?)
            """, (file_path, file_hash, datetime.now().isoformat(), chunks_count, "completed"))
            conn.commit()
        finally:
            conn.close()
    
    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
            total_processed = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT SUM(chunks_count) FROM processed_files")
            total_chunks = cursor.fetchone()[0] or 0
            
            return {
                'total_processed_files': total_processed,
                'total_chunks': total_chunks
            }
        finally:
            conn.close()
    
    def get_unprocessed_files(self, all_files: List[str]) -> List[str]:
        """Get list of unprocessed files"""
        unprocessed = []
        for file_path in all_files:
            if not self.is_file_processed(file_path):
                unprocessed.append(file_path)
        return unprocessed

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
    
    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            if self.conn is None or self.conn.closed != 0:
                logger.info("🔄 Reconnecting to database...")
                return self.connect()
            
            # Verify connection is actually alive
            try:
                # Create a temporary cursor for the check to avoid messing with the main cursor
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return True
            except Exception:
                logger.warning("⚠️  Connection appears dead, reconnecting...")
                return self.connect()
                
        except Exception as e:
            logger.error(f"❌ Connection check failed: {e}")
            return self.connect()
    
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
        if not self.ensure_connection():
            return False
            
        try:
            # Convert embedding to proper vector format for PostgreSQL
            if case.embedding:
                # Make sure embedding is a list, not a string
                if isinstance(case.embedding, str):
                    logger.error(f"❌ Embedding is a string, not a list! First 100 chars: {case.embedding[:100]}")
                    return False
                # Convert to proper array format: [1.0,2.0,3.0] not [[1,.,0,,,2,.,0,,,3,.,0]]
                embedding_str = '[' + ','.join([str(float(x)) for x in case.embedding]) + ']'
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
            if not self.ensure_connection():
                logger.error("❌ Database connection not available for search")
                return []
            
            if not self.conn or not self.cursor:
                logger.error("❌ Database connection not available for search")
                return []
            
            # Convert embedding to proper vector format for PostgreSQL
            embedding_str = '[' + ','.join([str(float(x)) for x in query_embedding]) + ']'
            
            # First check if we have any cases with embeddings
            self.cursor.execute("SELECT COUNT(*) as count FROM medical_cases WHERE embedding IS NOT NULL")
            count_result = self.cursor.fetchone()
            total_with_embeddings = count_result['count'] if count_result else 0
            
            if total_with_embeddings == 0:
                logger.warning(f"⚠️  No cases with embeddings found in database")
                return []
            
            logger.info(f"🔍 Searching {total_with_embeddings} cases with embeddings...")
            logger.debug(f"Query embedding format: {embedding_str[:100]}... (length: {len(embedding_str)})")
            
            query_dim = len(query_embedding)
            logger.info(f"📊 Query embedding dimension: {query_dim}")
            
            # Try the search query directly
            try:
                # First, test if we can do a simple vector operation
                # Try using <-> (L2 distance) instead of <=> (cosine distance) as a test
                logger.debug(f"Testing vector search with embedding string length: {len(embedding_str)}")
                
                # Use cosine distance (<=>) which returns 0 for identical, 1 for orthogonal, 2 for opposite
                # Convert to similarity: 1 - distance (so 1 = identical, 0 = orthogonal)
                self.cursor.execute("""
                    SELECT case_id,
                           content,
                           metadata,
                           1 - (embedding <=> %s::vector) as similarity,
                           embedding <=> %s::vector as distance
                    FROM medical_cases
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding_str, embedding_str, embedding_str, limit))
                
                results = self.cursor.fetchall()
                logger.info(f"✅ Found {len(results)} similar cases")
                
                if results:
                    # Log the top result's similarity
                    top_result = results[0]
                    top_similarity = top_result.get('similarity', 0)
                    top_distance = top_result.get('distance', 999)
                    logger.info(f"📈 Top result: {top_result.get('case_id', 'unknown')} - Similarity: {top_similarity:.4f}, Distance: {top_distance:.4f}")
                else:
                    logger.warning("⚠️  Query returned 0 results - checking if vector search is working...")
                    # Try a test query to see if we can get ANY results
                    self.cursor.execute("""
                        SELECT case_id, LEFT(content, 200) as content, metadata
                        FROM medical_cases 
                        WHERE embedding IS NOT NULL
                        LIMIT 1
                    """)
                    test_result = self.cursor.fetchone()
                    if test_result:
                        logger.info(f"✅ Database has cases, but vector search returned no results")
                    else:
                        logger.error("❌ No cases found in database at all")
                
                return [dict(row) for row in results]
            except Exception as query_error:
                logger.error(f"❌ Query execution error: {query_error}", exc_info=True)
                # Rollback the transaction to clear the error state
                self.conn.rollback()
                # Try a fallback query without similarity calculation
                try:
                    logger.info("🔄 Trying fallback query...")
                    self.cursor.execute("""
                        SELECT case_id, content, metadata, 0.5 as similarity
                        FROM medical_cases 
                        WHERE embedding IS NOT NULL
                        LIMIT %s
                    """, (limit,))
                    results = self.cursor.fetchall()
                    logger.info(f"✅ Fallback query returned {len(results)} cases")
                    return [dict(row) for row in results]
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback query also failed: {fallback_error}")
                    self.conn.rollback()
                    return []
        except Exception as e:
            logger.error(f"❌ Failed to search similar cases: {e}", exc_info=True)
            return []
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        """Get a specific medical case by ID or partial match"""
        if not self.ensure_connection():
            return None
            
        try:
            # First try exact match
            self.cursor.execute("""
                SELECT case_id, content, metadata, created_at
                FROM medical_cases 
                WHERE case_id = %s
            """, (case_id,))
            
            result = self.cursor.fetchone()
            if result:
                return dict(result)
            
            # If no exact match, try partial match for chunked cases
            # Remove .txt extension if present and look for chunks
            base_case_id = case_id.replace('.txt', '')
            self.cursor.execute("""
                SELECT case_id, content, metadata, created_at
                FROM medical_cases 
                WHERE case_id LIKE %s
                ORDER BY case_id
            """, (f"{base_case_id}%",))
            
            results = self.cursor.fetchall()
            if results:
                # Return the first chunk as the main case
                return dict(results[0])
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get case {case_id}: {e}")
            return None
    
    def get_case_chunks_by_id(self, base_case_id: str) -> List[Dict]:
        """Get all chunks for a specific case by base case ID"""
        if not self.ensure_connection():
            return []
            
        try:
            self.cursor.execute("""
                SELECT case_id, content, metadata, created_at
                FROM medical_cases 
                WHERE case_id LIKE %s
                ORDER BY case_id
            """, (f"{base_case_id}%",))
            
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Failed to get case chunks for {base_case_id}: {e}")
            return []
    
    def save_query_history(self, query: str, case_id: str, answer: str, confidence: float, processing_time: float):
        """Save query to history"""
        if not self.ensure_connection():
            return False
            
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
        if not self.ensure_connection():
            return {}
            
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
    """Main Medical RAG System with caching"""
    
    def __init__(self, neon_connection_string: str, clinicalbert_available: bool = None):
        self.neon_db = NeonRAGDatabase(neon_connection_string)
        self.cache = ProcessingCache()
        
        # Use provided parameter or fall back to global
        clinicalbert_available = clinicalbert_available if clinicalbert_available is not None else CLINICALBERT_AVAILABLE
        
        # Initialize ClinicalBERT
        if clinicalbert_available:
            try:
                self.model_name = "emilyalsentzer/Bio_ClinicalBERT"
                logger.info("🔄 Initializing ClinicalBERT...")
                
                # Try to load tokenizer first
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                logger.info("✅ ClinicalBERT tokenizer loaded")
                
                # Try to load model
                self.model = AutoModel.from_pretrained(self.model_name)
                logger.info("✅ ClinicalBERT model loaded")
                
                # Try to create QA pipeline
                try:
                    self.qa_pipeline = pipeline(
                        "question-answering",
                        model=self.model_name,
                        tokenizer=self.tokenizer,
                        device=0 if torch.cuda.is_available() else -1
                    )
                    logger.info("✅ ClinicalBERT QA pipeline initialized successfully")
                except Exception as qa_e:
                    logger.warning(f"⚠️  Could not initialize QA pipeline for {self.model_name} (this is normal for embedding-only models): {qa_e}")
                    self.qa_pipeline = None
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize ClinicalBERT: {e}")
                logger.warning("⚠️  Continuing without ClinicalBERT - using fallback analysis")
                self.model = None
                self.tokenizer = None
                self.qa_pipeline = None
        else:
            self.model = None
            self.tokenizer = None
            self.qa_pipeline = None
        
        # Initialize OpenAI client for answer generation
        self.openai_client = None
        openai_key = os.getenv('OPENAI_API_KEY')
        if OPENAI_AVAILABLE and openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("✅ OpenAI client initialized for answer generation")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize OpenAI: {e}")

        # RAG configuration
        self.retrieval_top_k = int(os.getenv('RETRIEVAL_TOP_K', 5))
        self.context_window = int(os.getenv('CONTEXT_WINDOW', 4000))
        self.max_tokens = int(os.getenv('MAX_TOKENS', 2000))
        self.temperature = float(os.getenv('TEMPERATURE', 0.1))
    
    def chunk_text(self, text: str, max_tokens: int = 6000, overlap: int = 200) -> List[str]:
        """Split text into chunks that fit within token limits"""
        try:
            # Initialize tokenizer for text-embedding-ada-002
            encoding = tiktoken.get_encoding("cl100k_base")
            
            # Split text into sentences for better chunking
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            chunks = []
            current_chunk = ""
            current_tokens = 0
            
            for sentence in sentences:
                sentence_tokens = len(encoding.encode(sentence))
                
                # If adding this sentence would exceed the limit, save current chunk
                if current_tokens + sentence_tokens > max_tokens and current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    current_tokens = len(encoding.encode(current_chunk))
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
                    current_tokens += sentence_tokens
            
            # Add the last chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Failed to chunk text: {e}")
            # Fallback: simple character-based chunking
            chunk_size = max_tokens * 4  # Rough estimate: 4 characters per token
            chunks = []
            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())
            return chunks
    
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
    
    def generate_answer(self, query: str, context_cases: List[Dict]) -> Tuple[str, float]:
        """Generate answer using OpenAI GPT (primary), ClinicalBERT QA (secondary), or enhanced extraction (fallback)"""
        # Primary: OpenAI GPT for synthesized answers
        if self.openai_client and context_cases:
            try:
                return self._generate_openai_answer(query, context_cases)
            except Exception as e:
                logger.warning(f"OpenAI generation failed, falling back: {e}")
        # Secondary: ClinicalBERT QA pipeline
        if self.qa_pipeline and context_cases:
            try:
                return self._generate_qa_answer(query, context_cases)
            except Exception as e:
                logger.warning(f"QA pipeline failed, falling back to enhanced answer: {e}")
        return self._generate_enhanced_answer(query, context_cases)

    def _generate_openai_answer(self, query: str, context_cases: List[Dict]) -> Tuple[str, float]:
        """Generate a synthesized answer using OpenAI GPT with retrieved case context"""
        # Build context from retrieved cases
        context_parts = []
        for i, case in enumerate(context_cases, 1):
            content = case.get('content', '')
            case_id = case.get('case_id', f'case_{i}')
            similarity = case.get('similarity', 0)
            # Limit each case to ~1500 chars to stay within token limits
            truncated = content[:1500]
            context_parts.append(f"--- Case {i} ({case_id}, relevance: {similarity:.2f}) ---\n{truncated}")

        context_text = "\n\n".join(context_parts)

        system_prompt = """You are a medical AI assistant analyzing clinical cases from a hospital database.
You provide evidence-based answers grounded in the retrieved medical cases.
- Synthesize information across cases to answer the query
- Cite specific case IDs when referencing findings
- Be precise and clinically relevant
- If the cases don't contain enough information to fully answer the query, say so
- Always include a disclaimer about consulting medical professionals"""

        user_prompt = f"""Based on the following retrieved medical cases, answer this clinical query:

**Query:** {query}

**Retrieved Cases:**
{context_text}

Provide a clear, structured answer with key findings, relevant diagnoses/treatments, and case citations."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

        answer = response.choices[0].message.content

        # Calculate confidence from similarity scores
        similarities = [c.get('similarity', 0) for c in context_cases if c.get('similarity')]
        confidence = sum(similarities) / len(similarities) if similarities else 0.5

        formatted_answer = f"""{answer}

**Analysis Details:**
- Answer synthesized by GPT-4o-mini from {len(context_cases)} retrieved cases
- Retrieval: ClinicalBERT embeddings + Neon PostgreSQL pgvector
- Average case relevance: {confidence:.2f}"""

        return formatted_answer, confidence

    def _generate_qa_answer(self, query: str, context_cases: List[Dict]) -> Tuple[str, float]:
        """Generate answer using ClinicalBERT QA pipeline"""
        # Build context from retrieved cases
        qa_results = []
        for case in context_cases:
            content = case.get('content', '')
            if not content:
                continue
            # Truncate to 512 tokens for the QA model
            truncated = content[:2000]
            try:
                result = self.qa_pipeline(question=query, context=truncated)
                if result and result.get('score', 0) > 0.01:
                    qa_results.append({
                        'answer': result['answer'],
                        'score': result['score'],
                        'case_id': case.get('case_id', 'unknown'),
                        'similarity': case.get('similarity', 0)
                    })
            except Exception:
                continue

        if not qa_results:
            return self._generate_enhanced_answer(query, context_cases)

        # Sort by score and build answer
        qa_results.sort(key=lambda x: x['score'], reverse=True)

        # Calculate confidence from actual similarity scores
        avg_similarity = sum(c.get('similarity', 0) for c in context_cases) / len(context_cases)
        top_qa_score = qa_results[0]['score']
        confidence = min(0.5 * avg_similarity + 0.5 * top_qa_score, 1.0)

        answer_parts = ["**Key Findings (ClinicalBERT QA):**"]
        seen_answers = set()
        for r in qa_results[:5]:
            ans_text = r['answer'].strip()
            if ans_text and ans_text.lower() not in seen_answers:
                seen_answers.add(ans_text.lower())
                answer_parts.append(f"- **{r['case_id']}** (relevance {r['score']:.2f}): {ans_text}")

        # Also extract structured sections for context
        section_info = self._extract_structured_info(query, context_cases)
        if section_info:
            answer_parts.append("")
            answer_parts.append(section_info)

        answer_text = "\n".join(answer_parts)
        formatted_answer = f"""Based on analysis of {len(context_cases)} relevant medical cases:

{answer_text}

**Analysis Details:**
- ClinicalBERT question-answering pipeline
- Cases retrieved from vector database (Neon PostgreSQL with pgvector)
- Confidence: {confidence:.2f}

**Note:** This analysis is based on similar medical cases in the database. Always consult with qualified medical professionals for clinical decisions."""

        return formatted_answer, confidence

    def _extract_structured_info(self, query: str, context_cases: List[Dict]) -> str:
        """Extract structured medical info from cases relevant to the query type"""
        query_lower = query.lower()
        parts = []

        query_keywords = {
            'diagnosis': ['diagnosis', 'diagnosed', 'condition', 'disease', 'disorder'],
            'symptoms': ['symptoms', 'signs', 'presenting', 'complaint', 'experience'],
            'treatment': ['treatment', 'therapy', 'medication', 'management', 'intervention', 'prescribed'],
            'test': ['test', 'lab', 'results', 'findings', 'imaging', 'study'],
        }

        query_type = None
        for qtype, keywords in query_keywords.items():
            if any(kw in query_lower for kw in keywords):
                query_type = qtype
                break

        section_map = {
            'diagnosis': (['diagnosis', 'impression', 'assessment'], "Diagnoses Found"),
            'symptoms': (['chief complaint', 'cc:', 'presenting complaint', 'history of present illness', 'hpi'], "Clinical Presentations"),
            'treatment': (['medications', 'current medications', 'meds', 'discharge medications'], "Treatment Information"),
            'test': (['laboratory', 'lab results', 'imaging', 'studies', 'pertinent results'], "Test Results"),
        }

        if query_type and query_type in section_map:
            keywords, header = section_map[query_type]
            findings = []
            for case in context_cases:
                section = self._extract_section(case.get('content', ''), keywords)
                if section:
                    findings.append(f"- {case.get('case_id', 'unknown')}: {section[:300]}")
            if findings:
                parts.append(f"**{header}:**")
                parts.extend(findings[:5])

        return "\n".join(parts)
    
    def _generate_enhanced_answer(self, query: str, context_cases: List[Dict]) -> Tuple[str, float]:
        """Generate enhanced answer with semantic understanding"""
        try:
            query_lower = query.lower()
            
            # Extract relevant information from each case
            relevant_findings = []
            all_content = ""
            
            for case in context_cases:
                content = case['content']
                all_content += content + "\n\n"
                case_id = case['case_id']
                
                # Extract key sections from medical notes
                sections = {
                    'chief_complaint': self._extract_section(content, ['chief complaint', 'cc:', 'presenting complaint']),
                    'diagnosis': self._extract_section(content, ['diagnosis', 'impression', 'assessment']),
                    'history': self._extract_section(content, ['history of present illness', 'hpi', 'history']),
                    'medications': self._extract_section(content, ['medications', 'current medications', 'meds']),
                    'allergies': self._extract_section(content, ['allergies', 'drug allergies']),
                    'vitals': self._extract_section(content, ['vital signs', 'vitals', 'physical exam'])
                }
                
                relevant_findings.append({
                    'case_id': case_id,
                    'sections': sections,
                    'content': content
                })
            
            # Calculate confidence from actual similarity scores returned by vector search
            if context_cases:
                similarities = [c.get('similarity', 0) for c in context_cases if c.get('similarity')]
                confidence = sum(similarities) / len(similarities) if similarities else 0.5
            else:
                confidence = 0.0
            
            # Build comprehensive answer
            answer_parts = []
            
            # Identify what type of query this is
            query_keywords = {
                'diagnosis': ['diagnosis', 'diagnosed', 'condition', 'disease', 'disorder'],
                'symptoms': ['symptoms', 'signs', 'presenting', 'complaint', 'experience'],
                'treatment': ['treatment', 'therapy', 'medication', 'management', 'intervention'],
                'test': ['test', 'lab', 'results', 'findings', 'imaging', 'study'],
                'prognosis': ['prognosis', 'outcome', 'recovery', 'survival']
            }
            
            query_type = None
            for qtype, keywords in query_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    query_type = qtype
                    break
            
            # Generate answer based on query type and relevant findings
            if query_type == 'diagnosis':
                diagnoses = []
                for finding in relevant_findings:
                    if finding['sections']['diagnosis']:
                        diagnoses.append(f"- {finding['case_id']}: {finding['sections']['diagnosis'][:200]}")
                
                if diagnoses:
                    answer_parts.append("**Diagnoses Found:**")
                    answer_parts.extend(diagnoses[:5])
            
            elif query_type == 'symptoms':
                symptoms = []
                for finding in relevant_findings:
                    if finding['sections']['chief_complaint']:
                        symptoms.append(f"- {finding['case_id']}: {finding['sections']['chief_complaint'][:200]}")
                    elif finding['sections']['history']:
                        symptoms.append(f"- {finding['case_id']}: {finding['sections']['history'][:200]}")
                
                if symptoms:
                    answer_parts.append("**Clinical Presentations:**")
                    answer_parts.extend(symptoms[:5])
            
            elif query_type == 'treatment':
                treatments = []
                for finding in relevant_findings:
                    if finding['sections']['medications']:
                        treatments.append(f"- {finding['case_id']}: {finding['sections']['medications'][:200]}")
                
                if treatments:
                    answer_parts.append("**Treatment Information:**")
                    answer_parts.extend(treatments[:5])
            
            # If no specific query type or no structured findings, provide general summary
            if not answer_parts:
                # Use semantic search to find most relevant excerpts
                excerpts = []
                for finding in relevant_findings[:3]:
                    content = finding['content']
                    # Find sentences containing query terms
                    sentences = re.split(r'(?<=[.!?])\s+', content)
                    relevant_sentences = []
                    for sentence in sentences:
                        if any(term in sentence.lower() for term in query_lower.split()):
                            relevant_sentences.append(sentence)
                    
                    if relevant_sentences:
                        excerpt = ' '.join(relevant_sentences[:3])
                        if len(excerpt) > 300:
                            excerpt = excerpt[:300] + "..."
                        excerpts.append(f"- {finding['case_id']}: {excerpt}")
                
                if excerpts:
                    answer_parts.append("**Relevant Information:**")
                    answer_parts.extend(excerpts)
                else:
                    # Provide first 300 chars of each case as context
                    for finding in relevant_findings[:3]:
                        excerpt = finding['content'][:300] + "..."
                        answer_parts.append(f"- {finding['case_id']}: {excerpt}")
            
            # Format final answer
            if answer_parts:
                answer_text = "\n".join(answer_parts)
                formatted_answer = f"""Based on analysis of {len(context_cases)} relevant medical cases:

{answer_text}

**Analysis Details:**
- Semantic similarity search with ClinicalBERT embeddings
- Cases retrieved from vector database (Neon PostgreSQL with pgvector)
- Confidence based on semantic similarity: {confidence:.2f}

**Note:** This analysis is based on similar medical cases in the database. Always consult with qualified medical professionals for clinical decisions."""
            else:
                formatted_answer = f"""Based on {len(context_cases)} medical cases retrieved:

The query "{query}" has been matched against the medical case database. The cases contain relevant medical information, though specific details matching your exact query may require further review.

**Retrieved Cases:**
{', '.join([f['case_id'] for f in relevant_findings])}

**Note:** For specific medical information, please review the full case details or consult with qualified medical professionals."""
                confidence = 0.6
            
            return formatted_answer, confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to generate enhanced answer: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_answer(query, context_cases)
    
    def _extract_section(self, content: str, keywords: List[str]) -> str:
        """Extract a section from medical note based on keywords"""
        try:
            content_lower = content.lower()
            for keyword in keywords:
                # Find the keyword
                idx = content_lower.find(keyword)
                if idx != -1:
                    # Extract text after the keyword until next section or 300 chars
                    start = idx + len(keyword)
                    # Skip past any colons or line breaks
                    while start < len(content) and content[start] in ':\n\r ':
                        start += 1
                    
                    # Find end (next section header or max length)
                    end = start + 300
                    extract = content[start:end].strip()
                    
                    # Try to end at a sentence boundary
                    last_period = extract.rfind('.')
                    if last_period > 50:
                        extract = extract[:last_period + 1]
                    
                    return extract
            return ""
        except:
            return ""
    
    def _generate_fallback_answer(self, query: str, context_cases: List[Dict]) -> Tuple[str, float]:
        """Generate fallback answer when ClinicalBERT is not available"""
        try:
            # Simple keyword-based analysis
            query_lower = query.lower()
            query_terms = [term.strip() for term in query_lower.split(',')]
            
            # Analyze each case for relevance
            relevant_info = []
            confidence_score = 0.0
            
            for i, case in enumerate(context_cases, 1):
                case_content = case['content'].lower()
                case_id = case['case_id']
                
                # Check for query term matches
                matches = []
                for term in query_terms:
                    if term in case_content:
                        matches.append(term)
                
                if matches:
                    relevant_info.append(f"Case {i} ({case_id}): Found terms: {', '.join(matches)}")
                    confidence_score += 0.3  # Base confidence for each relevant case
            
            # Normalize confidence
            confidence_score = min(confidence_score, 1.0)
            
            # Generate answer
            if relevant_info:
                answer = f"""Based on the medical cases provided, here is my analysis:

**Answer:** The query "{query}" relates to the following medical conditions and findings in the provided cases.

**Key Findings:**
- Analysis based on {len(context_cases)} relevant medical cases
- Found relevant information in {len(relevant_info)} cases
- Confidence score: {confidence_score:.2f}

**Relevant Cases:**
{chr(10).join(relevant_info[:5])}  # Limit to first 5 cases

**Medical Context:**
The analysis is derived from medical case data in the database. The cases contain information relevant to your query.

**Note:** This is a keyword-based analysis. For more sophisticated analysis, ClinicalBERT AI model is required. Always consult with qualified medical professionals for clinical decisions."""
            else:
                answer = f"""Based on the medical cases provided, here is my analysis:

**Answer:** No specific matches found for the query "{query}" in the provided cases.

**Key Findings:**
- Analysis based on {len(context_cases)} relevant medical cases
- No direct keyword matches found
- Confidence score: {confidence_score:.2f}

**Medical Context:**
The cases may contain relevant information, but no direct matches were found for the specific query terms.

**Note:** This is a keyword-based analysis. For more sophisticated analysis, ClinicalBERT AI model is required. Always consult with qualified medical professionals for clinical decisions."""
            
            return answer, confidence_score
            
        except Exception as e:
            logger.error(f"❌ Failed to generate fallback answer: {e}")
            return f"❌ Error generating fallback answer: {e}", 0.0
    
    def query_medical_cases(self, query: str, case_id: Optional[str] = None) -> RAGResult:
        """Query medical cases using RAG"""
        start_time = datetime.now()
        
        try:
            # If specific case requested, prioritize it and get all its chunks
            if case_id:
                # Get all chunks for this case
                base_case_id = case_id.replace('.txt', '')
                case_chunks = self.neon_db.get_case_chunks_by_id(base_case_id)
                if case_chunks:
                    # Use the specific case chunks as the primary results
                    similar_cases = case_chunks
                    
                    # Generate answer using the specific case
                    answer, confidence = self.generate_answer(query, similar_cases)
                    
                    # Prepare sources
                    sources = [case['case_id'] for case in similar_cases]
                    
                    # Calculate processing time
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    # Save to history
                    self.neon_db.save_query_history(query, case_id, answer, confidence, processing_time)
                    
                    return RAGResult(
                        query=query,
                        relevant_cases=similar_cases,
                        answer=answer,
                        confidence=confidence,
                        processing_time=processing_time,
                        sources=sources
                    )
            
            # Get embedding for query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                logger.error("❌ Failed to generate query embedding")
                return RAGResult(
                    query=query,
                    relevant_cases=[],
                    answer="❌ Failed to get query embedding",
                    confidence=0.0,
                    processing_time=0.0,
                    sources=[]
                )
            
            logger.info(f"🔍 Query embedding generated (dimension: {len(query_embedding)})")
            
            # Check database connection and try to reconnect if needed
            if not self.neon_db.conn:
                logger.warning("⚠️  Database connection lost - attempting to reconnect...")
                if self.neon_db.connect():
                    logger.info("✅ Reconnected to database")
                else:
                    logger.error("❌ Database connection not available and reconnection failed")
                    return RAGResult(
                        query=query,
                        relevant_cases=[],
                        answer="❌ Database connection not available. Please check your internet connection or database credentials.",
                        confidence=0.0,
                        processing_time=0.0,
                        sources=[]
                    )
            
            # Search for similar cases
            similar_cases = self.neon_db.search_similar_cases(query_embedding, limit=self.retrieval_top_k)
            
            if not similar_cases:
                return RAGResult(
                    query=query,
                    relevant_cases=[],
                    answer="❌ No relevant cases found",
                    confidence=0.0,
                    processing_time=0.0,
                    sources=[]
                )
            
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
    
    def process_medical_cases_incremental(self, cases_directory: str, force_reprocess: bool = False):
        """Process medical cases incrementally with caching"""
        if not self.neon_db.connect():
            return False
        
        if not self.neon_db.create_tables():
            return False
        
        cases_path = Path(cases_directory)
        if not cases_path.exists():
            logger.error(f"❌ Cases directory not found: {cases_directory}")
            return False
        
        case_files = list(cases_path.glob("*.txt"))
        
        # Get unprocessed files
        if force_reprocess:
            unprocessed_files = case_files
            logger.info(f"🔄 Force reprocessing all {len(case_files)} files")
        else:
            unprocessed_files = self.cache.get_unprocessed_files([str(f) for f in case_files])
            logger.info(f"📁 Found {len(unprocessed_files)} unprocessed files out of {len(case_files)} total")
        
        if not unprocessed_files:
            logger.info("✅ All files already processed!")
            return True
        
        processed = 0
        total_chunks = 0
        
        for file_path in unprocessed_files:
            try:
                # Convert Path object to string if needed
                file_path_str = str(file_path)
                with open(file_path_str, 'r', encoding='utf-8') as f:
                    case_content = f.read()
                
                # Chunk the content to avoid token limits
                chunks = self.chunk_text(case_content)
                logger.info(f"📄 {Path(file_path_str).stem}: Split into {len(chunks)} chunks")
                
                # Process each chunk as a separate case
                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    
                    # Get embedding for this chunk
                    embedding = self.get_embedding(chunk)
                    if not embedding:
                        logger.warning(f"⚠️  Skipping chunk {i+1} of {Path(file_path_str).stem} - no embedding")
                        continue
                    
                    # Create medical case for this chunk
                    chunk_id = f"{Path(file_path_str).stem}_chunk_{i+1}"
                    medical_case = MedicalCase(
                        case_id=chunk_id,
                        content=chunk,
                        embedding=embedding,
                        metadata={
                            'original_file': Path(file_path_str).stem,
                            'chunk_index': i + 1,
                            'total_chunks': len(chunks),
                            'file_path': file_path_str,
                            'content_length': len(chunk),
                            'processed_at': datetime.now().isoformat()
                        }
                    )
                    
                    # Insert into database
                    if self.neon_db.insert_medical_case(medical_case):
                        total_chunks += 1
                    else:
                        logger.warning(f"⚠️  Failed to insert chunk {i+1} of {Path(file_path_str).stem}")
                
                # Mark file as processed
                self.cache.mark_file_processed(file_path_str, len(chunks))
                processed += 1
                
                if processed % 10 == 0:
                    logger.info(f"📊 Processed {processed}/{len(unprocessed_files)} files, {total_chunks} total chunks")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {file_path_str}: {e}")
        
        logger.info(f"✅ Processed {processed} new files into {total_chunks} chunks")
        return True

# Flask web interface
# Flask web interface
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_secret_key_change_in_prod')
CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple User class
class User(UserMixin):
    def __init__(self, id):
        self.id = id
        
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple hardcoded check - in production use a database
        admin_user = os.getenv('ADMIN_USER', 'admin')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'medical_rag_2025')
        
        if username == admin_user and password == admin_pass:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# HTML template for web interface
@app.route('/')
@login_required
def index():
    """Main web interface"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - Public for monitoring"""
    return jsonify({
        'status': 'healthy',
        'neon_available': NEON_AVAILABLE,
        'clinicalbert_available': CLINICALBERT_AVAILABLE,
        'rag_system_initialized': rag_system is not None,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/medical_query', methods=['POST'])
def medical_query():
    """Query medical cases with better error handling"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        query = data.get('query', '')
        case_id = data.get('case_id')
        
        if not rag_system:
            return jsonify({'success': False, 'error': 'RAG system not initialized'}), 500
        
        if not query:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        result = rag_system.query_medical_cases(query, case_id)
        
        return jsonify({
            'success': True,
            'query': result.query,
            'answer': result.answer,
            'confidence': result.confidence,
            'processing_time': result.processing_time,
            'sources': result.sources,
            'relevant_cases': len(result.relevant_cases)
        })
    except Exception as e:
        logger.error(f"❌ Medical query error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system_stats', methods=['GET'])
@login_required
def system_stats():
    """Get system statistics"""
    try:
        if not rag_system or not rag_system.neon_db.conn:
            return jsonify({'success': False, 'error': 'Database not connected'}), 500
        
        stats = rag_system.neon_db.get_system_stats()
        cache_stats = rag_system.cache.get_processing_stats()
        
        return jsonify({
            'success': True, 
            'stats': stats,
            'cache_stats': cache_stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def main():
    """Main function to run the optimized medical RAG system"""
    global rag_system
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    neon_connection = os.getenv('NEON_CONNECTION_STRING')
    openai_key = os.getenv('OPENAI_API_KEY')

    if not neon_connection:
        logger.error("❌ NEON_CONNECTION_STRING not found in environment")
        return

    if not openai_key:
        logger.warning("⚠️  OPENAI_API_KEY not found — answer generation will use fallback mode")
    
    # Initialize RAG system
    rag_system = MedicalRAGSystem(neon_connection, CLINICALBERT_AVAILABLE)
    
    # Try to connect to database (optional)
    if not rag_system.neon_db.connect():
        logger.warning("⚠️  Database connection failed - some features may be limited")
    
    # Process cases incrementally if directory exists and database is connected
    # Use current directory/data by default
    current_dir = os.getcwd()
    cases_dir = os.path.join(current_dir, "data")
    
    if os.path.exists(cases_dir) and rag_system.neon_db.conn:
        logger.info(f"🔄 Processing medical cases incrementally from {cases_dir}...")
        rag_system.process_medical_cases_incremental(cases_dir)
    elif os.path.exists(cases_dir):
        logger.warning("⚠️  Database not connected - skipping case processing")
    else:
        logger.info(f"📁 No cases directory found at {cases_dir} - starting with empty database")
    
    # Start web server
    port = int(os.getenv('FLASK_PORT', 5557))
    logger.info(f"🌐 Starting Optimized Medical RAG System on port {port}")
    logger.info(f"📱 Access at: http://localhost:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    main()

