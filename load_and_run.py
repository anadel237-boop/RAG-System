#!/usr/bin/env python3
"""
Clinical Insight Bot — Application Launcher

Loads medical case data and starts the web server.
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Resolve paths relative to this script's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

import optimized_medical_rag_system as rag_module


def main():
    """Initialize the RAG system and start the web server."""
    neon_connection = os.getenv('NEON_CONNECTION_STRING')
    if not neon_connection:
        rag_module.logger.error("NEON_CONNECTION_STRING not found in environment. See env.example.")
        sys.exit(1)

    # Initialize RAG system (ClinicalBERT is loaded locally, no API key needed)
    rag_module.rag_system = rag_module.MedicalRAGSystem(
        neon_connection, rag_module.CLINICALBERT_AVAILABLE
    )

    # Connect to the vector database
    if not rag_module.rag_system.neon_db.connect():
        rag_module.logger.warning("Database connection failed — some features may be limited")

    # Process medical cases if data directory exists
    if os.path.exists(DATA_DIR) and rag_module.rag_system.neon_db.conn:
        case_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.txt')]
        rag_module.logger.info(f"Found {len(case_files)} case files to process...")
        rag_module.rag_system.process_medical_cases_incremental(DATA_DIR)
    elif os.path.exists(DATA_DIR):
        rag_module.logger.warning("Database not connected — skipping case processing")
    else:
        rag_module.logger.error(f"Cases directory not found: {DATA_DIR}")

    # Start web server
    port = int(os.getenv('FLASK_PORT', 5557))
    debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    rag_module.logger.info(f"Starting Clinical Insight Bot on port {port}")
    rag_module.logger.info(f"Access at: http://localhost:{port}")

    rag_module.app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == "__main__":
    main()
