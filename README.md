# Clinical Insight Bot: A Retrieval-Augmented Generation System for Preoperative Assessment

**Supplementary Code Repository**

Companion code for: *"Clinical Insight Bot for Preoperative Assessment: A Retrieval-Augmented Generation System for Rapid Identification of Critical Comorbidities in Anesthesia Practice"*

---

## Overview

This repository contains the source code, configuration, and evaluation scripts for a Retrieval-Augmented Generation (RAG) system designed to rapidly identify critical comorbidities from medical records for preoperative anesthesia assessment. The system uses ClinicalBERT embeddings with a Neon PostgreSQL vector database to perform semantic similarity search across 1,000 de-identified medical cases (1,680 text chunks).

## System Architecture

The system comprises four core components:

1. **NeonRAGDatabase** — Vector database operations using PostgreSQL with pgvector (HNSW indexing)
2. **MedicalRAGSystem** — Core RAG logic with ClinicalBERT (768-dimensional embeddings)
3. **ProcessingCache** — SQLite-based caching for efficient reprocessing
4. **Web Interface** — Flask backend with Next.js frontend for interactive querying

### Data Flow

Medical cases are ingested, chunked (1,000 tokens with 200-token overlap), embedded via ClinicalBERT, and stored in the vector database. User queries follow the same embedding pipeline and retrieve the top-k most similar chunks via cosine similarity search, with structured answer generation from retrieved context.

## Requirements

- Python 3.10 or higher
- Node.js 18+ (for the frontend)
- A Neon PostgreSQL database with the pgvector extension enabled
- 4 GB RAM minimum (8 GB recommended for model loading)

## Setup

### 1. Clone and Configure

```bash
git clone <repository-url>
cd Medical_RAG_System_Neon_clinicalBERT

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp env.example .env
# Edit .env with your Neon PostgreSQL connection string
```

### 2. Obtain Medical Case Data

The system uses de-identified cases from the MIMIC-III database. Access requires PhysioNet credentialing. See [PHYSIONET_GUIDE.md](PHYSIONET_GUIDE.md) for instructions on obtaining and formatting the data.

Place case files in the `data/` directory as `case_XXXX_mimic.txt`.

### 3. Start the System

```bash
python3 load_and_run.py
# Access at http://localhost:5557
```

Alternatively, use Docker:

```bash
docker-compose up --build
```

### 4. Run Evaluation Tests

```bash
cd tests/
python3 test_system.py          # System validation
python3 test_symptom_query.py   # Symptom-based queries
python3 test_procedure_query.py # Procedure queries
```

## Project Structure

```
Medical_RAG_System_Neon_clinicalBERT/
├── optimized_medical_rag_system.py   # Main RAG system
├── load_and_run.py                   # Application launcher
├── medical_rag_mcp_server.py         # MCP server integration
├── ingest_physionet.py               # Data ingestion pipeline
├── fix_vector_index.py               # Vector index maintenance
├── requirements.txt                  # Python dependencies
├── env.example                       # Environment template
├── Dockerfile                        # Container configuration
├── docker-compose.yml                # Container orchestration
├── MANUSCRIPT_MEDICAL_JOURNAL.md     # Full manuscript text
├── PHYSIONET_GUIDE.md                # Data access instructions
├── README_DOCKER.md                  # Docker deployment guide
├── data/                             # Medical case files (1,000 cases)
├── frontend/                         # Next.js web interface
├── templates/                        # Flask HTML templates
├── static/                           # Static assets (CSS, JS)
├── tests/                            # Evaluation and test scripts
├── test_data/                        # Sample test datasets
└── figures/                          # Result visualizations
```

## API Endpoints

| Method | Endpoint              | Description                    |
|--------|-----------------------|--------------------------------|
| GET    | `/`                   | Web interface                  |
| POST   | `/api/medical_query`  | Submit a clinical query        |
| POST   | `/api/patient_query`  | Patient-specific query         |
| GET    | `/api/system_stats`   | System performance statistics  |
| GET    | `/api/health`         | Health check                   |

### Example Query

```python
import requests

response = requests.post('http://localhost:5557/api/medical_query', json={
    'query': 'diabetes mellitus with hypertension'
})
print(response.json())
```

## Performance Summary

| Metric                  | Value                        |
|-------------------------|------------------------------|
| Total cases indexed     | 1,000                        |
| Total text chunks       | 1,680                        |
| Embedding dimension     | 768 (ClinicalBERT)          |
| Mean query response time| 1.02 s (range: 0.04-2.01 s) |
| Confidence score        | 0.85 (consistent)            |
| Retrieval success rate  | 98.7%                        |

## Database Schema

```sql
CREATE TABLE medical_cases (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cases_embedding ON medical_cases
USING hnsw (embedding vector_cosine_ops);
```

## Environment Configuration

See `env.example` for all configurable parameters. Key settings:

| Variable                 | Default | Description                          |
|--------------------------|---------|--------------------------------------|
| `NEON_CONNECTION_STRING` | --      | PostgreSQL connection URI (required)  |
| `FLASK_PORT`             | 5557    | Web server port                      |
| `VECTOR_DIMENSION`       | 768     | ClinicalBERT embedding dimension     |
| `RETRIEVAL_TOP_K`        | 5       | Number of cases to retrieve per query|
| `CHUNK_SIZE`             | 1000    | Maximum tokens per text chunk        |
| `CHUNK_OVERLAP`          | 200     | Token overlap between chunks         |

## Ethical Considerations

This system uses publicly available, de-identified data from the MIMIC-III database. No new patient data was collected. The system is intended as a research tool and clinical decision support prototype. It does not replace clinical judgment and all output must be validated by qualified medical professionals.

## Citation

If you use this code in your research, please cite:

> [Author names]. Clinical Insight Bot for Preoperative Assessment: A Retrieval-Augmented Generation System for Rapid Identification of Critical Comorbidities in Anesthesia Practice. *Anesthesia & Analgesia*. [Year].

## License

This software is released under the MIT License. See [LICENSE](LICENSE) for details.

Medical case data from MIMIC-III is subject to the PhysioNet Credentialed Health Data Use Agreement.

## Acknowledgments

- ClinicalBERT: Emily Alsentzer et al. (2019)
- MIMIC-III: MIT Laboratory for Computational Physiology
- Neon: Serverless PostgreSQL platform
- pgvector: Open-source vector similarity search for PostgreSQL
