# Medical RAG System Cleanup Plan

## Essential Files (KEEP) ✅

### Core System Files
- `medical_rag_system.py` - Original Flask-based system
- `optimized_medical_rag_system.py` - **MAIN RECOMMENDED SYSTEM**
- `medical_rag_fastapi_improved.py` - FastAPI-based system
- `medical_rag_mcp_server.py` - MCP server for integration

### Data & Database
- `data/` - **1000 medical cases (ESSENTIAL)**
- `processing_cache.db` - **Processing cache (ESSENTIAL)**
- `.env` - **Environment configuration (ESSENTIAL)**

### Configuration & Documentation
- `README.md` - Project documentation
- `SOLUTION_GUIDE.md` - Solution guide
- `PROJECT_REVIEW_AND_BACKUP_PLAN.md` - Project review
- `requirements.txt` - Dependencies
- `env.example` - Environment template

### Virtual Environment
- `venv/` - **Python virtual environment (ESSENTIAL)**

### Test Results (Keep Latest)
- `rag_accuracy_test_20251017_191249.json` - **Latest test results (KEEP)**
- `simple_accuracy_test.py` - Test script

### Utility Scripts (Keep Core Ones)
- `run_optimized_system.py` - Quick startup script
- `test_optimized_system.py` - System test

## Files to REMOVE 🗑️

### Duplicate/Outdated Test Results
- `rag_accuracy_test_20251017_131940.json` - Older test result
- `rag_accuracy_test_20251017_132755.json` - Older test result  
- `rag_accuracy_test_20251017_191151.json` - Older test result

### Debug/Development Files
- `debug_system.py` - Debug script
- `simple_debug.py` - Debug script
- `temp_reprocess.py` - Temporary file

### Fix/Utility Scripts (No Longer Needed)
- `fix_embedding_format.py` - One-time fix script
- `fix_embeddings.py` - One-time fix script
- `fix_fastapi_database.py` - One-time fix script
- `fix_vector_dimensions.py` - One-time fix script
- `reprocess_cases.py` - One-time reprocessing script

### Test/Development Scripts
- `check_database.py` - Database check script
- `check_neon_status.py` - Status check script
- `configure_credentials.py` - Credential setup (redundant)
- `manual_setup.py` - Manual setup script
- `quick_test_setup.py` - Quick test setup
- `run_with_credentials.py` - Alternative runner
- `run_with_venv.py` - Alternative runner
- `run_without_db.py` - Alternative runner
- `setup_credentials.py` - Setup script
- `simple_test_server.py` - Test server
- `test_credentials.py` - Credential test
- `test_improved_fastapi.py` - FastAPI test
- `test_query.py` - Query test
- `test_rag_accuracy.py` - Accuracy test (redundant)
- `test_rag_query.py` - Query test
- `test_with_venv.py` - Venv test
- `working_fastapi.py` - Working FastAPI (redundant)

### Outdated System Files
- `medical_rag_fastapi.py` - **Outdated FastAPI version (REMOVE)**

### System Files
- `.DS_Store` - macOS system file
- `__pycache__/` - Python cache directory
- `setup.sh` - Setup script (redundant)

## Cleanup Commands

```bash
# Remove older test results (keep only the latest)
rm rag_accuracy_test_20251017_131940.json
rm rag_accuracy_test_20251017_132755.json  
rm rag_accuracy_test_20251017_191151.json

# Remove debug/development files
rm debug_system.py
rm simple_debug.py
rm temp_reprocess.py

# Remove fix scripts (one-time use)
rm fix_embedding_format.py
rm fix_embeddings.py
rm fix_fastapi_database.py
rm fix_vector_dimensions.py
rm reprocess_cases.py

# Remove test/development scripts
rm check_database.py
rm check_neon_status.py
rm configure_credentials.py
rm manual_setup.py
rm quick_test_setup.py
rm run_with_credentials.py
rm run_with_venv.py
rm run_without_db.py
rm setup_credentials.py
rm simple_test_server.py
rm test_credentials.py
rm test_improved_fastapi.py
rm test_query.py
rm test_rag_accuracy.py
rm test_rag_query.py
rm test_with_venv.py
rm working_fastapi.py

# Remove outdated system files
rm medical_rag_fastapi.py

# Remove system files
rm .DS_Store
rm -rf __pycache__/
rm setup.sh
```

## After Cleanup - Essential Files Only

### Core System (4 files)
- `medical_rag_system.py`
- `optimized_medical_rag_system.py` ⭐ **MAIN**
- `medical_rag_fastapi_improved.py`
- `medical_rag_mcp_server.py`

### Data & Config (4 items)
- `data/` (1000 medical cases)
- `processing_cache.db`
- `.env`
- `venv/`

### Documentation (4 files)
- `README.md`
- `SOLUTION_GUIDE.md`
- `PROJECT_REVIEW_AND_BACKUP_PLAN.md`
- `requirements.txt`
- `env.example`

### Test Results (2 files)
- `rag_accuracy_test_20251017_191249.json`
- `simple_accuracy_test.py`

### Utilities (2 files)
- `run_optimized_system.py`
- `test_optimized_system.py`

**Total: ~16 essential files vs 40+ current files**

