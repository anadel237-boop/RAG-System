#!/usr/bin/env python3
"""
Medical RAG System with Neon Vector Database
Retrieval-Augmented Generation system for medical case analysis
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
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
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

# ClinicalBERT integration
try:
    from transformers import AutoModel, AutoTokenizer, pipeline
    import torch
    CLINICALBERT_AVAILABLE = True
except ImportError:
    CLINICALBERT_AVAILABLE = False
    print("⚠️  ClinicalBERT not available. Install with: pip install transformers torch")

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
            self.cursor.execute("""
                INSERT INTO medical_cases (case_id, content, embedding, metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (case_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
            """, (
                case.case_id,
                case.content,
                case.embedding,
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
                self.model_name = "emilyalsentzer/Bio_ClinicalBERT"
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name)
                self.qa_pipeline = pipeline(
                    "question-answering",
                    model=self.model_name,
                    tokenizer=self.tokenizer,
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info("✅ ClinicalBERT initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize ClinicalBERT: {e}")
                self.model = None
                self.tokenizer = None
                self.qa_pipeline = None
        else:
            self.model = None
            self.tokenizer = None
            self.qa_pipeline = None
        
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
        
        try:
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
                if case:
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
    
    def process_medical_cases(self, cases_directory: str):
        """Process all medical cases and store in Neon"""
        if not self.neon_db.connect():
            return False
        
        if not self.neon_db.create_tables():
            return False
        
        cases_path = Path(cases_directory)
        if not cases_path.exists():
            logger.error(f"❌ Cases directory not found: {cases_directory}")
            return False
        
        case_files = list(cases_path.glob("*.txt"))
        logger.info(f"📁 Processing {len(case_files)} medical cases...")
        
        processed = 0
        total_chunks = 0
        
        for case_file in case_files:
            try:
                with open(case_file, 'r', encoding='utf-8') as f:
                    case_content = f.read()
                
                # Chunk the content to avoid token limits
                chunks = self.chunk_text(case_content)
                logger.info(f"📄 {case_file.stem}: Split into {len(chunks)} chunks")
                
                # Process each chunk as a separate case
                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    
                    # Get embedding for this chunk
                    embedding = self.get_embedding(chunk)
                    if not embedding:
                        logger.warning(f"⚠️  Skipping chunk {i+1} of {case_file.stem} - no embedding")
                        continue
                    
                    # Create medical case for this chunk
                    chunk_id = f"{case_file.stem}_chunk_{i+1}"
                    medical_case = MedicalCase(
                        case_id=chunk_id,
                        content=chunk,
                        embedding=embedding,
                        metadata={
                            'original_file': case_file.stem,
                            'chunk_index': i + 1,
                            'total_chunks': len(chunks),
                            'file_path': str(case_file),
                            'content_length': len(chunk),
                            'processed_at': datetime.now().isoformat()
                        }
                    )
                    
                    # Insert into database
                    if self.neon_db.insert_medical_case(medical_case):
                        total_chunks += 1
                    else:
                        logger.warning(f"⚠️  Failed to insert chunk {i+1} of {case_file.stem}")
                
                processed += 1
                if processed % 50 == 0:
                    logger.info(f"📊 Processed {processed}/{len(case_files)} cases, {total_chunks} total chunks")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {case_file}: {e}")
        
        logger.info(f"✅ Processed {processed} medical cases into {total_chunks} chunks")
        return True

# Flask web interface
app = Flask(__name__)
CORS(app)

# Global RAG system instance
rag_system = None

# HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medical RAG System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #34495e; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        textarea { height: 100px; resize: vertical; }
        button { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #2980b9; }
        .result { margin-top: 20px; padding: 20px; background: #ecf0f1; border-radius: 5px; }
        .confidence { color: #27ae60; font-weight: bold; }
        .processing-time { color: #7f8c8d; font-size: 12px; }
        .sources { margin-top: 15px; }
        .source { background: #e8f4f8; padding: 5px 10px; margin: 5px 0; border-radius: 3px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Medical RAG System with Neon</h1>
        
        <form id="queryForm">
            <div class="form-group">
                <label for="query">Medical Query:</label>
                <textarea id="query" name="query" placeholder="Enter your medical question or symptoms..." required></textarea>
            </div>
            
            <div class="form-group">
                <label for="case_id">Specific Case ID (optional):</label>
                <input type="text" id="case_id" name="case_id" placeholder="e.g., case_0001_mimic.txt">
            </div>
            
            <button type="submit">🔍 Query Medical Cases</button>
        </form>
        
        <div id="result" class="result" style="display: none;">
            <h3>📊 Analysis Results</h3>
            <div id="answer"></div>
            <div id="metadata"></div>
            <div id="sources" class="sources"></div>
        </div>
    </div>

    <script>
        document.getElementById('queryForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const query = document.getElementById('query').value;
            const caseId = document.getElementById('case_id').value;
            
            try {
                const response = await fetch('/api/medical_query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, case_id: caseId || null })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('answer').innerHTML = result.answer.replace(/\\n/g, '<br>');
                    document.getElementById('metadata').innerHTML = `
                        <p><span class="confidence">Confidence: ${result.confidence}</span> | 
                        <span class="processing-time">Processing Time: ${result.processing_time}s</span></p>
                    `;
                    
                    let sourcesHtml = '<h4>📚 Sources:</h4>';
                    result.sources.forEach(source => {
                        sourcesHtml += `<div class="source">${source}</div>`;
                    });
                    document.getElementById('sources').innerHTML = sourcesHtml;
                    
                    document.getElementById('result').style.display = 'block';
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'neon_available': NEON_AVAILABLE,
        'clinicalbert_available': CLINICALBERT_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/medical_query', methods=['POST'])
def medical_query():
    """Query medical cases"""
    try:
        data = request.json
        query = data.get('query', '')
        case_id = data.get('case_id')
        
        if not rag_system:
            return jsonify({'error': 'RAG system not initialized'}), 500
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/patient_query', methods=['POST'])
def patient_query():
    """Patient-specific query"""
    try:
        data = request.json
        patient_id = data.get('patient_id', '')
        symptoms = data.get('symptoms', [])
        
        if not patient_id:
            return jsonify({'error': 'Patient ID is required'}), 400
        
        # Create query from symptoms
        query = f"Patient {patient_id} with symptoms: {', '.join(symptoms)}"
        
        result = rag_system.query_medical_cases(query, patient_id)
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'query': result.query,
            'answer': result.answer,
            'confidence': result.confidence,
            'processing_time': result.processing_time,
            'sources': result.sources
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system_stats', methods=['GET'])
def system_stats():
    """Get system statistics"""
    try:
        if not rag_system or not rag_system.neon_db.conn:
            return jsonify({'error': 'Database not connected'}), 500
        
        stats = rag_system.neon_db.get_system_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def main():
    """Main function to run the medical RAG system"""
    global rag_system
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    neon_connection = os.getenv('NEON_CONNECTION_STRING')
    
    if not neon_connection:
        logger.error("❌ NEON_CONNECTION_STRING not found in environment")
        return
    
    # Initialize RAG system
    rag_system = MedicalRAGSystem(neon_connection)
    
    # Try to connect to database (optional)
    rag_system.neon_db.connect()
    
    # Process cases if directory exists and database is connected
    cases_dir = "/Users/saiofocalallc/Medical_RAG_System_Neon/data"
    if os.path.exists(cases_dir) and rag_system.neon_db.conn:
        logger.info("🔄 Processing medical cases...")
        rag_system.process_medical_cases(cases_dir)
    elif os.path.exists(cases_dir):
        logger.warning("⚠️  Database not connected - skipping case processing")
    else:
        logger.info("📁 No cases directory found - starting with empty database")
    
    # Start web server
    port = int(os.getenv('FLASK_PORT', 5557))
    logger.info(f"🌐 Starting Medical RAG System on port {port}")
    logger.info(f"📱 Access at: http://localhost:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    main()





