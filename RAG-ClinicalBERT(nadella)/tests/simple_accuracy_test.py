#!/usr/bin/env python3
"""
Simple Medical RAG System Accuracy Testing
Tests the accuracy of the RAG system directly without web interface.
"""

import os
import json
import random
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re
from datetime import datetime

# Import the optimized RAG system components
from optimized_medical_rag_system import MedicalRAGSystem, MedicalCase
from dotenv import load_dotenv

class SimpleRAGAccuracyTester:
    """Test RAG system accuracy directly"""
    
    def __init__(self):
        load_dotenv()
        
        # Initialize RAG system
        neon_connection = os.getenv('NEON_CONNECTION_STRING')
        
        if not neon_connection:
            raise ValueError("Missing environment variables")
        
        # Initialize with optimized system
        try:
            from optimized_medical_rag_system import CLINICALBERT_AVAILABLE
            self.rag_system = MedicalRAGSystem(neon_connection, CLINICALBERT_AVAILABLE)
        except ImportError:
            self.rag_system = MedicalRAGSystem(neon_connection)
        
        # Connect to database
        if not self.rag_system.neon_db.connect():
            raise RuntimeError("Failed to connect to database")
        
        print("✅ RAG system initialized successfully")
    
    def load_sample_cases(self, cases_dir: str, num_samples: int = 10) -> List[Dict[str, Any]]:
        """Load random sample cases for testing"""
        cases_path = Path(cases_dir)
        if not cases_path.exists():
            raise FileNotFoundError(f"Cases directory not found: {cases_dir}")
        
        # Get all case files
        case_files = list(cases_path.glob("*.txt"))
        if not case_files:
             print(f"⚠️  No text files found in {cases_dir}")
             return []

        if len(case_files) < num_samples:
            num_samples = len(case_files)
        
        # Randomly select cases
        selected_cases = random.sample(case_files, num_samples)
        
        sample_cases = []
        for case_file in selected_cases:
            try:
                with open(case_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract key information from the case
                case_info = self.extract_case_info(content, case_file.stem)
                sample_cases.append(case_info)
                
            except Exception as e:
                print(f"⚠️  Error loading {case_file}: {e}")
                continue
        
        return sample_cases
    
    def extract_case_info(self, content: str, case_id: str) -> Dict[str, Any]:
        """Extract key information from a medical case"""
        info = {
            'case_id': case_id,
            'content': content,
            'chief_complaint': '',
            'diagnosis': '',
            'symptoms': [],
            'medications': [],
            'procedures': [],
            'age_sex': '',
            'service': ''
        }
        
        # Extract chief complaint
        chief_complaint_match = re.search(r'Chief Complaint:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if chief_complaint_match:
            info['chief_complaint'] = chief_complaint_match.group(1).strip()
        
        # Extract diagnosis (look for common patterns)
        diagnosis_patterns = [
            r'Diagnosis:\s*(.+?)(?:\n|$)',
            r'Final Diagnosis:\s*(.+?)(?:\n|$)',
            r'Discharge Diagnosis:\s*(.+?)(?:\n|$)'
        ]
        for pattern in diagnosis_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                info['diagnosis'] = match.group(1).strip()
                break
        
        # Extract service
        service_match = re.search(r'Service:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if service_match:
            info['service'] = service_match.group(1).strip()
        
        # Extract age and sex
        age_sex_match = re.search(r'(\d+)\s*yo\s*([MF])', content, re.IGNORECASE)
        if age_sex_match:
            info['age_sex'] = f"{age_sex_match.group(1)}yo {age_sex_match.group(2)}"
        
        # Extract symptoms (common medical terms)
        symptom_keywords = [
            'pain', 'fever', 'nausea', 'vomiting', 'diarrhea', 'constipation',
            'shortness of breath', 'chest pain', 'headache', 'dizziness',
            'fatigue', 'weakness', 'confusion', 'seizure', 'syncope'
        ]
        for symptom in symptom_keywords:
            if symptom.lower() in content.lower():
                info['symptoms'].append(symptom)
        
        return info
    
    def create_test_queries(self, case_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create test queries based on case information"""
        queries = []
        
        # Query 1: Chief complaint based
        if case_info['chief_complaint']:
            queries.append({
                'query': f"Patient with {case_info['chief_complaint']} - what are the treatment options?",
                'expected_case': case_info['case_id'],
                'query_type': 'chief_complaint'
            })
        
        # Query 2: Symptom-based
        if case_info['symptoms']:
            symptoms_text = ', '.join(case_info['symptoms'][:3])  # Use first 3 symptoms
            queries.append({
                'query': f"Patient presenting with {symptoms_text} - differential diagnosis?",
                'expected_case': case_info['case_id'],
                'query_type': 'symptoms'
            })
        
        # Query 3: Service-based
        if case_info['service']:
            queries.append({
                'query': f"Cases in {case_info['service']} service - what are common conditions?",
                'expected_case': case_info['case_id'],
                'query_type': 'service'
            })
            
        # Fallback if no specific info found, use general query
        if not queries:
             queries.append({
                'query': f"Summary of case {case_info['case_id']}",
                'expected_case': case_info['case_id'],
                'query_type': 'general'
             })
        
        return queries
    
    def test_rag_query(self, query: str, expected_case: str = None) -> Dict[str, Any]:
        """Test a single RAG query"""
        try:
            start_time = time.time()
            
            result = self.rag_system.query_medical_cases(query, expected_case)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'query': query,
                'expected_case': expected_case,
                'answer': result.answer,
                'confidence': result.confidence,
                'processing_time': processing_time,
                'sources': result.sources,
                'relevant_cases': len(result.relevant_cases),
                'found_expected_case': expected_case in [s.split('_chunk')[0] for s in result.sources] if expected_case else None
            }
                
        except Exception as e:
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def run_accuracy_test(self, cases_dir: str, num_samples: int = 10) -> Dict[str, Any]:
        """Run comprehensive accuracy test"""
        print(f"🧪 Starting RAG Accuracy Test with {num_samples} sample cases...")
        
        # Load sample cases
        sample_cases = self.load_sample_cases(cases_dir, num_samples)
        
        if not sample_cases:
            return {'error': 'No cases loaded'}
            
        print(f"📁 Loaded {len(sample_cases)} sample cases")
        
        # Create test queries
        all_queries = []
        for case in sample_cases:
            queries = self.create_test_queries(case)
            all_queries.extend(queries)
        
        print(f"❓ Created {len(all_queries)} test queries")
        
        # Test each query
        results = []
        for i, query_info in enumerate(all_queries):
            print(f"🔍 Testing query {i+1}/{len(all_queries)}: {query_info['query'][:50]}...")
            
            result = self.test_rag_query(
                query_info['query'],
                query_info['expected_case']
            )
            result['query_type'] = query_info['query_type']
            results.append(result)
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.5)
        
        # Analyze results
        analysis = self.analyze_results(results)
        
        return {
            'test_summary': {
                'total_queries': len(results),
                'successful_queries': len([r for r in results if r['success']]),
                'failed_queries': len([r for r in results if not r['success']]),
                'test_timestamp': datetime.now().isoformat()
            },
            'results': results,
            'analysis': analysis
        }
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test results and calculate accuracy metrics"""
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            return {'error': 'No successful queries to analyze'}
        
        # Calculate metrics
        total_queries = len(results)
        successful_queries = len(successful_results)
        success_rate = successful_queries / total_queries if total_queries > 0 else 0
        
        # Confidence analysis
        confidences = [r['confidence'] for r in successful_results if 'confidence' in r]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Processing time analysis
        processing_times = [r['processing_time'] for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Case retrieval accuracy
        case_retrieval_results = [r for r in successful_results if r.get('found_expected_case') is not None]
        case_retrieval_accuracy = sum(r['found_expected_case'] for r in case_retrieval_results) / len(case_retrieval_results) if case_retrieval_results else 0
        
        # Query type analysis
        query_type_performance = {}
        for result in successful_results:
            query_type = result.get('query_type', 'unknown')
            if query_type not in query_type_performance:
                query_type_performance[query_type] = {'count': 0, 'avg_confidence': 0, 'confidences': []}
            query_type_performance[query_type]['count'] += 1
            if 'confidence' in result:
                query_type_performance[query_type]['confidences'].append(result['confidence'])
        
        # Calculate average confidence per query type
        for qtype in query_type_performance:
            confidences = query_type_performance[qtype]['confidences']
            query_type_performance[qtype]['avg_confidence'] = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'success_rate': round(success_rate * 100, 2),
            'average_confidence': round(avg_confidence, 3),
            'average_processing_time': round(avg_processing_time, 2),
            'case_retrieval_accuracy': round(case_retrieval_accuracy * 100, 2),
            'query_type_performance': query_type_performance,
            'total_successful_queries': successful_queries,
            'total_failed_queries': total_queries - successful_queries
        }
    
    def print_results(self, test_results: Dict[str, Any]):
        """Print formatted test results"""
        print("\n" + "="*60)
        print("🏥 MEDICAL RAG SYSTEM ACCURACY TEST RESULTS")
        print("="*60)
        
        if 'error' in test_results:
             print(f"❌ Error: {test_results['error']}")
             return

        summary = test_results['test_summary']
        analysis = test_results['analysis']
        
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Queries: {summary['total_queries']}")
        print(f"   Successful: {summary['successful_queries']}")
        print(f"   Failed: {summary['failed_queries']}")
        print(f"   Success Rate: {analysis['success_rate']}%")
        
        print(f"\n🎯 ACCURACY METRICS:")
        print(f"   Average Confidence: {analysis['average_confidence']}")
        print(f"   Case Retrieval Accuracy: {analysis['case_retrieval_accuracy']}%")
        print(f"   Average Processing Time: {analysis['average_processing_time']}s")
        
        print(f"\n📈 QUERY TYPE PERFORMANCE:")
        for qtype, perf in analysis['query_type_performance'].items():
            print(f"   {qtype.title()}: {perf['count']} queries, avg confidence: {perf['avg_confidence']:.3f}")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for i, result in enumerate(test_results['results'][:5]):  # Show first 5 results
            status = "✅" if result['success'] else "❌"
            confidence = result.get('confidence', 0)
            retrieved = "Match" if result.get('found_expected_case') else "Miss"
            print(f"   {status} Query {i+1}: {result['query'][:50]}... (Conf: {confidence:.3f}, {retrieved})")
        
        if len(test_results['results']) > 5:
            print(f"   ... and {len(test_results['results']) - 5} more results")
        
        print("\n" + "="*60)

def main():
    """Main function to run accuracy tests"""
    # Configuration
    # Use current directory data folder
    cases_directory = os.path.join(os.getcwd(), "data")
    num_samples = 5  # Test with 5 random cases for speed
    
    try:
        # Check if directory exists
        if not os.path.exists(cases_directory):
             print(f"❌ Data directory not found: {cases_directory}")
             return

        # Initialize tester
        tester = SimpleRAGAccuracyTester()
        
        # Run accuracy test
        results = tester.run_accuracy_test(cases_directory, num_samples)
        
        # Print results
        tester.print_results(results)
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"rag_accuracy_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
    except Exception as e:
        print(f"❌ Error running accuracy test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()