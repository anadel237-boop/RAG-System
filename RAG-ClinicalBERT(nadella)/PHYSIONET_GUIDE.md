# Using PhysioNet Data (MIMIC-III/IV)

This guide explains how to use clinical notes from PhysioNet (specifically MIMIC-III or MIMIC-IV) to test the Medical RAG System with more data.

## Prerequisites

1.  **PhysioNet Access**: You must have a credentialed PhysioNet account and signed the Data Use Agreement (DUA).
2.  **Access to MIMIC**: You need specific access to MIMIC-III Clinical Database or MIMIC-IV-Note.

## Steps to Ingest Data

### 1. Download the Data
Go to [PhysioNet](https://physionet.org/) and download the clinical notes CSV.
*   **MIMIC-III**: Download `NOTEEVENTS.csv.gz` (unzip to get `NOTEEVENTS.csv`).
*   **MIMIC-IV**: Download `discharge.csv.gz` or `radiology.csv.gz`.

### 2. Run the Ingestion Script
We have provided a script `ingest_physionet.py` to convert these CSVs into the format our system expects.

```bash
# Install pandas if not already installed
pip install pandas

# Run the script (replace path with your actual CSV location)
# We recommend using a limit first to test
python ingest_physionet.py /path/to/NOTEEVENTS.csv --limit 500
```

This will:
1.  Read the CSV.
2.  Extract the clinical text.
3.  Create individual `.txt` files in the `data/` directory.

### 3. Restart the System
Once the files are in `data/`, restart the RAG system. It will automatically detect the new files and generate embeddings for them.

```bash
./stop_server.sh
./start_server.sh
```

## Note on Processing Time
Processing thousands of notes takes time!
*   The system generates embeddings for each note using ClinicalBERT.
*   Start with a small batch (e.g., 100-500 notes) to verify everything works before ingesting the full dataset.
