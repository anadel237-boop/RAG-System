#!/usr/bin/env python3
"""
Quick startup script for the optimized medical RAG system
"""

import os
import sys
from pathlib import Path

def main():
    """Run the optimized medical RAG system"""
    
    # Check if we're in the right directory
    if not Path("optimized_medical_rag_system.py").exists():
        print("❌ optimized_medical_rag_system.py not found in current directory")
        print("Please run this script from the Medical_RAG_System_Neon directory")
        return
    
    # Check for environment variables
    if not os.getenv('NEON_CONNECTION_STRING'):
        print("❌ NEON_CONNECTION_STRING not found in environment")
        print("Please set your Neon database connection string")
        return
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key")
        return
    
    print("🚀 Starting Optimized Medical RAG System...")
    print("📊 This system will:")
    print("   - Only process new/unmodified files")
    print("   - Cache processing progress")
    print("   - Resume from where it left off")
    print("   - Handle web interface errors better")
    print()
    
    # Import and run the optimized system
    try:
        from optimized_medical_rag_system import main as run_system
        run_system()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed")
    except Exception as e:
        print(f"❌ Error running system: {e}")

if __name__ == "__main__":
    main()

