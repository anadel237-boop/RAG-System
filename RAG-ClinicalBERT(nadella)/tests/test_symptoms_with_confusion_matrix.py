#!/usr/bin/env python3
"""
Symptom-Based Medical RAG System Testing with Confusion Matrix
Tests symptom queries and generates confusion matrix visualization
"""

import os
import json
import time
import requests
from typing import List, Dict, Any
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import re
from sklearn.metrics import confusion_matrix, classification_report

class SymptomRAGTester:
    """Test RAG system with symptom-based queries"""
    
    def __init__(self, api_url: str = "http://localhost:5557"):
        self.api_url = api_url
        self.test_results = []
        
    def test_symptom_query(self, query: str, case_id: str = None) -> Dict[str, Any]:
        """Test a single symptom query"""
        try:
            url = f"{self.api_url}/api/medical_query"
            payload = {"query": query}
            if case_id:
                payload["case_id"] = case_id
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            result['test_query'] = query
            result['test_case_id'] = case_id
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_query': query,
                'test_case_id': case_id
            }
    
    def run_symptom_tests(self) -> List[Dict[str, Any]]:
        """Run comprehensive symptom-based tests"""
        print("🧪 Starting Symptom-Based RAG Tests...\n")
        
        # Define test cases with symptoms
        test_cases = [
            {
                'symptom': 'chest pain',
                'query': 'chest pain',
                'expected_conditions': ['cardiac', 'coronary', 'myocardial', 'angina']
            },
            {
                'symptom': 'shortness of breath',
                'query': 'shortness of breath',
                'expected_conditions': ['respiratory', 'pulmonary', 'pneumonia', 'COPD']
            },
            {
                'symptom': 'chest pain and shortness of breath',
                'query': 'chest pain and shortness of breath',
                'expected_conditions': ['cardiac', 'pulmonary', 'heart failure']
            },
            {
                'symptom': 'acid reflux',
                'query': 'acid reflux',
                'expected_conditions': ['GERD', 'esophageal', 'gastric', 'reflux']
            },
            {
                'symptom': 'abdominal pain',
                'query': 'abdominal pain',
                'expected_conditions': ['gastrointestinal', 'appendicitis', 'bowel']
            },
            {
                'symptom': 'fever and cough',
                'query': 'fever and cough',
                'expected_conditions': ['pneumonia', 'respiratory infection', 'bronchitis']
            }
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            print(f"🔍 Test {i+1}/{len(test_cases)}: {test_case['symptom']}")
            
            result = self.test_symptom_query(test_case['query'])
            result['expected_conditions'] = test_case['expected_conditions']
            result['symptom'] = test_case['symptom']
            results.append(result)
            
            if result.get('success'):
                print(f"   ✅ Found {result.get('relevant_cases', 0)} cases")
                print(f"   📊 Confidence: {result.get('confidence', 0):.3f}")
                print(f"   ⏱️  Time: {result.get('processing_time', 0):.2f}s")
                if result.get('sources'):
                    print(f"   📁 Top case: {result['sources'][0]}")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            
            print()
            time.sleep(2)  # Avoid overwhelming the server
        
        return results
    
    def test_patient_specific_symptoms(self, data_dir: str, num_cases: int = 10) -> List[Dict[str, Any]]:
        """Test symptom queries with specific patient IDs"""
        print(f"\n🏥 Testing Patient-Specific Symptom Queries...\n")
        
        # Get available case files
        data_path = Path(data_dir)
        case_files = list(data_path.glob("case_*.txt"))[:num_cases]
        
        results = []
        for i, case_file in enumerate(case_files):
            case_id = case_file.name
            
            # Read case content to identify symptoms
            try:
                with open(case_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract symptoms from case
                symptoms = self.extract_symptoms(content)
                
                if symptoms:
                    query = f"diagnosis for {', '.join(symptoms[:2])}"
                    print(f"🔍 Test {i+1}/{len(case_files)}: {case_id}")
                    print(f"   Symptoms: {', '.join(symptoms[:3])}")
                    
                    result = self.test_symptom_query(query, case_id)
                    result['extracted_symptoms'] = symptoms
                    results.append(result)
                    
                    if result.get('success'):
                        print(f"   ✅ Query succeeded")
                        print(f"   📊 Confidence: {result.get('confidence', 0):.3f}")
                    else:
                        print(f"   ❌ Failed")
                    print()
                
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
            
            time.sleep(1)
        
        return results
    
    def extract_symptoms(self, content: str) -> List[str]:
        """Extract symptoms from medical case text"""
        symptom_keywords = [
            'chest pain', 'shortness of breath', 'dyspnea', 'fever', 'cough',
            'nausea', 'vomiting', 'diarrhea', 'constipation', 'headache',
            'dizziness', 'fatigue', 'weakness', 'abdominal pain', 'back pain',
            'confusion', 'seizure', 'syncope', 'palpitations', 'sweating'
        ]
        
        found_symptoms = []
        content_lower = content.lower()
        
        for symptom in symptom_keywords:
            if symptom in content_lower:
                found_symptoms.append(symptom)
        
        return found_symptoms
    
    def create_confusion_matrix(self, results: List[Dict[str, Any]], save_dir: str = "."):
        """Create confusion matrix visualization"""
        print("\n📊 Generating Confusion Matrix...\n")
        
        # Prepare data for confusion matrix
        y_true = []  # Ground truth
        y_pred = []  # Predictions
        
        for result in results:
            if not result.get('success'):
                continue
            
            # Determine if result is relevant
            has_sources = len(result.get('sources', [])) > 0
            high_confidence = result.get('confidence', 0) >= 0.7
            
            y_true.append(1)  # Expected: relevant case found
            
            if has_sources and high_confidence:
                y_pred.append(1)  # Predicted: relevant
            else:
                y_pred.append(0)  # Predicted: not relevant
        
        if not y_true:
            print("⚠️  No data available for confusion matrix")
            return
        
        # Create confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        # Create figure with multiple subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Medical RAG System - Symptom Query Performance Analysis', 
                     fontsize=16, fontweight='bold')
        
        # 1. Confusion Matrix Heatmap
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['Not Retrieved', 'Retrieved'],
                    yticklabels=['Not Expected', 'Expected'],
                    ax=axes[0, 0], cbar_kws={'label': 'Count'})
        axes[0, 0].set_title('Confusion Matrix\n(Case Retrieval Performance)', fontsize=12, fontweight='bold')
        axes[0, 0].set_ylabel('Ground Truth', fontsize=10)
        axes[0, 0].set_xlabel('Predicted', fontsize=10)
        
        # 2. Confidence Distribution
        confidences = [r.get('confidence', 0) for r in results if r.get('success')]
        if confidences:
            axes[0, 1].hist(confidences, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
            axes[0, 1].axvline(np.mean(confidences), color='red', linestyle='--', 
                              linewidth=2, label=f'Mean: {np.mean(confidences):.3f}')
            axes[0, 1].set_title('Confidence Score Distribution', fontsize=12, fontweight='bold')
            axes[0, 1].set_xlabel('Confidence Score', fontsize=10)
            axes[0, 1].set_ylabel('Frequency', fontsize=10)
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Processing Time Analysis
        processing_times = [r.get('processing_time', 0) for r in results if r.get('success')]
        if processing_times:
            axes[1, 0].boxplot(processing_times, vert=True, patch_artist=True,
                              boxprops=dict(facecolor='lightgreen', alpha=0.7))
            axes[1, 0].set_title('Query Processing Time Distribution', fontsize=12, fontweight='bold')
            axes[1, 0].set_ylabel('Time (seconds)', fontsize=10)
            axes[1, 0].set_xticklabels(['All Queries'])
            axes[1, 0].grid(True, alpha=0.3, axis='y')
            
            stats_text = f"Mean: {np.mean(processing_times):.2f}s\nMedian: {np.median(processing_times):.2f}s"
            axes[1, 0].text(0.98, 0.98, stats_text, transform=axes[1, 0].transAxes,
                           verticalalignment='top', horizontalalignment='right',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 4. Relevant Cases Retrieved
        cases_retrieved = [r.get('relevant_cases', 0) for r in results if r.get('success')]
        if cases_retrieved:
            axes[1, 1].bar(range(len(cases_retrieved)), cases_retrieved, 
                          color='coral', alpha=0.7, edgecolor='black')
            axes[1, 1].axhline(np.mean(cases_retrieved), color='blue', linestyle='--',
                              linewidth=2, label=f'Mean: {np.mean(cases_retrieved):.1f}')
            axes[1, 1].set_title('Number of Relevant Cases Retrieved per Query', 
                                fontsize=12, fontweight='bold')
            axes[1, 1].set_xlabel('Query Index', fontsize=10)
            axes[1, 1].set_ylabel('Number of Cases', fontsize=10)
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save figure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"symptom_rag_confusion_matrix_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✅ Confusion matrix saved to: {filepath}")
        
        return cm
    
    def generate_report(self, results: List[Dict[str, Any]], save_dir: str = "."):
        """Generate comprehensive test report"""
        print("\n📝 Generating Test Report...\n")
        
        # Calculate metrics
        total_tests = len(results)
        successful_tests = len([r for r in results if r.get('success')])
        failed_tests = total_tests - successful_tests
        
        confidences = [r.get('confidence', 0) for r in results if r.get('success')]
        processing_times = [r.get('processing_time', 0) for r in results if r.get('success')]
        cases_retrieved = [r.get('relevant_cases', 0) for r in results if r.get('success')]
        
        report = {
            'test_summary': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': f"{(successful_tests/total_tests*100):.2f}%" if total_tests > 0 else "0%"
            },
            'performance_metrics': {
                'average_confidence': f"{np.mean(confidences):.3f}" if confidences else "N/A",
                'median_confidence': f"{np.median(confidences):.3f}" if confidences else "N/A",
                'min_confidence': f"{np.min(confidences):.3f}" if confidences else "N/A",
                'max_confidence': f"{np.max(confidences):.3f}" if confidences else "N/A",
                'average_processing_time': f"{np.mean(processing_times):.2f}s" if processing_times else "N/A",
                'median_processing_time': f"{np.median(processing_times):.2f}s" if processing_times else "N/A",
                'average_cases_retrieved': f"{np.mean(cases_retrieved):.1f}" if cases_retrieved else "N/A"
            },
            'test_results': results
        }
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(save_dir, f"symptom_rag_test_report_{timestamp}.json")
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Test report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {report['test_summary']['success_rate']}")
        print(f"\nAverage Confidence: {report['performance_metrics']['average_confidence']}")
        print(f"Average Processing Time: {report['performance_metrics']['average_processing_time']}")
        print(f"Average Cases Retrieved: {report['performance_metrics']['average_cases_retrieved']}")
        print("="*70)
        
        return report

def main():
    """Main function to run symptom tests with confusion matrix"""
    print("\n🏥 Medical RAG System - Symptom Testing with Confusion Matrix\n")
    print("="*70)
    
    # Configuration
    api_url = "http://localhost:5557"
    data_dir = "/Users/saiofocalallc/Medical_RAG_System_Neon_clinicalBERT/data"
    
    try:
        # Initialize tester
        tester = SymptomRAGTester(api_url)
        
        # Run general symptom tests
        print("\n🔬 PART 1: General Symptom Queries\n")
        symptom_results = tester.run_symptom_tests()
        
        # Run patient-specific symptom tests
        print("\n🔬 PART 2: Patient-Specific Symptom Queries\n")
        patient_results = tester.test_patient_specific_symptoms(data_dir, num_cases=10)
        
        # Combine results
        all_results = symptom_results + patient_results
        
        # Generate confusion matrix
        tester.create_confusion_matrix(all_results)
        
        # Generate comprehensive report
        tester.generate_report(all_results)
        
        print("\n✅ All tests completed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
