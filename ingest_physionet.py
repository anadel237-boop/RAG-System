import pandas as pd
import os
import csv
from tqdm import tqdm

def ingest_mimic_notes(csv_path, output_dir="data", limit=None):
    """
    Ingest clinical notes from MIMIC-III (NOTEEVENTS.csv) or MIMIC-IV (discharge.csv).
    Extracts text and saves as individual .txt files for the RAG system.
    """
    print(f"🏥 Processing PhysioNet data from: {csv_path}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")

    # Detect MIMIC version based on columns or filename
    # MIMIC-III: ROW_ID, SUBJECT_ID, HADM_ID, CHARTDATE, CHARTTIME, STORETIME, CATEGORY, DESCRIPTION, CGID, ISERROR, TEXT
    # MIMIC-IV: note_id, subject_id, hadm_id, note_type, note_seq, charttime, storetime, text
    
    try:
        # Read CSV in chunks to handle large files
        chunk_size = 1000
        processed_count = 0
        
        # Determine columns to use
        # We'll try to find 'TEXT' or 'text' column
        
        print("🔄 Reading CSV file...")
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            # Normalize columns to lowercase
            chunk.columns = [c.lower() for c in chunk.columns]
            
            if 'text' not in chunk.columns:
                print("❌ Error: Could not find 'text' column in CSV.")
                print(f"   Available columns: {list(chunk.columns)}")
                return

            for _, row in chunk.iterrows():
                text_content = row['text']
                
                # Create a unique filename
                # Prefer note_id (MIMIC-IV) or row_id (MIMIC-III)
                if 'note_id' in row:
                    file_id = str(row['note_id'])
                elif 'row_id' in row:
                    file_id = f"mimic_iii_{row['row_id']}"
                else:
                    # Fallback
                    file_id = f"note_{processed_count}"
                
                # Add metadata to the text file content if useful, 
                # but for now the system expects raw text or text with headers.
                # We'll prepend some metadata for the RAG to pick up.
                
                category = row.get('category', row.get('note_type', 'Unknown'))
                subject_id = row.get('subject_id', 'Unknown')
                
                full_content = f"Patient ID: {subject_id}\nCategory: {category}\n\n{text_content}"
                
                # Save to file
                filename = f"{file_id}.txt"
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                
                processed_count += 1
                
                if limit and processed_count >= limit:
                    print(f"✅ Reached limit of {limit} files.")
                    return

            print(f"   Processed {processed_count} notes...", end='\r')
            
        print(f"\n✅ Successfully converted {processed_count} notes to {output_dir}/")
        print("🚀 You can now restart the RAG system to ingest these new cases.")

    except Exception as e:
        print(f"\n❌ Error processing file: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Ingest PhysioNet Clinical Notes')
    parser.add_argument('csv_path', help='Path to the MIMIC CSV file (e.g., NOTEEVENTS.csv)')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of notes to process')
    parser.add_argument('--output', default='data', help='Output directory')
    
    args = parser.parse_args()
    
    ingest_mimic_notes(args.csv_path, args.output, args.limit)
