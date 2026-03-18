# Clinical Insight Bot — Code Explanations (Beginner Guide)

---

## What This Project Does

This is a **Medical RAG (Retrieval-Augmented Generation) System**. Think of it like a smart medical search engine:

1. You ask a medical question (e.g., "What are symptoms of a heart attack?")
2. It searches through 1,000+ real hospital case files to find the most relevant ones
3. It sends those cases to GPT, which reads them and writes you a clear answer

---

## The Key Files

### 1. `.env` — Your Secret Keys

```
NEON_CONNECTION_STRING=postgresql://...    ← password to your database
OPENAI_API_KEY=sk-proj-...                ← password to use GPT
FLASK_PORT=5557                           ← what port the website runs on
```

This is like a locked drawer with all your passwords. The code reads from here so you never hardcode secrets.

---

### 2. `load_and_run.py` — The Starter Button

```python
#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

import optimized_medical_rag_system as rag_module

def main():
    neon_connection = os.getenv('NEON_CONNECTION_STRING')
    if not neon_connection:
        rag_module.logger.error("NEON_CONNECTION_STRING not found")
        sys.exit(1)

    rag_module.rag_system = rag_module.MedicalRAGSystem(
        neon_connection, rag_module.CLINICALBERT_AVAILABLE
    )

    if not rag_module.rag_system.neon_db.connect():
        rag_module.logger.warning("Database connection failed")

    if os.path.exists(DATA_DIR) and rag_module.rag_system.neon_db.conn:
        rag_module.rag_system.process_medical_cases_incremental(DATA_DIR)

    port = int(os.getenv('FLASK_PORT', 5557))
    rag_module.app.run(host='0.0.0.0', port=port, debug=False)
```

Here's what each part does:

- **`load_dotenv()`** — Reads your `.env` file and loads the passwords into memory
- **`BASE_DIR / DATA_DIR`** — Figures out where the project folder and data folder are on your computer
- **`os.getenv('NEON_CONNECTION_STRING')`** — Grabs the database password. If it's missing, the program stops
- **`MedicalRAGSystem(...)`** — Creates the "brain" of the system with ClinicalBERT
- **`neon_db.connect()`** — Connects to the Neon cloud database
- **`process_medical_cases_incremental()`** — If the `data/` folder has `.txt` case files, it processes them into the database
- **`app.run()`** — Starts the website on port 5557 so you can open it in your browser

**Think of it like**: turning on a restaurant. You unlock the door (load passwords), check the kitchen is stocked (connect to database), prep ingredients (process cases), then open for customers (start the web server).

---

### 3. `optimized_medical_rag_system.py` — The Brain

This is the big file (~1300 lines). Here are the digestible pieces:

#### a) The Imports (lines 1-55)

```python
from transformers import AutoModel, AutoTokenizer, pipeline
from openai import OpenAI
import psycopg2       # talks to PostgreSQL database
from flask import Flask  # creates the website
```

These are like tools in a toolbox. Each `import` brings in someone else's pre-built code so you don't have to write everything from scratch.

#### b) Data Structures (lines 65-81)

```python
@dataclass
class MedicalCase:
    case_id: str                        # e.g., "case_0445_mimic"
    content: str                        # the actual medical text
    embedding: Optional[List[float]]    # the case converted to numbers
    metadata: Dict[str, Any]            # extra info (dates, tags, etc.)
```

A **dataclass** is like a form template. Every medical case has the same fields — an ID, content, embedding, and metadata. It's like saying "every patient chart must have a name, DOB, and diagnosis."

**What is an embedding?** It's the key concept:
- Computers can't understand words directly
- ClinicalBERT converts text like "chest pain" into a list of 768 numbers: `[0.23, -0.15, 0.87, ...]`
- Similar medical concepts get similar numbers
- "chest pain" and "cardiac discomfort" would have very close numbers
- This lets us do math to find similar cases

#### c) ProcessingCache (lines 83-130)

```python
class ProcessingCache:
    """Local cache to track processing progress"""
```

This keeps track of which case files have already been processed. Without it, every time you restart the server, it would re-process all 1,002 files. With the cache, it says "already done, skip!" — that's why you see `Found 0 unprocessed files out of 1002 total`.

#### d) MedicalRAGSystem — The Core Engine

```python
class MedicalRAGSystem:
    def __init__(self):       # set up ClinicalBERT + OpenAI
    def get_embedding(self):  # convert text → numbers
    def generate_answer(self): # create the final answer
    def query_medical_cases(self):  # the full pipeline
```

**`get_embedding()`** — How text becomes numbers:
```python
inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
with torch.no_grad():
    outputs = self.model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
```

Step by step:
1. **Tokenizer** breaks "chest pain" into tokens the model understands
2. **Model** (ClinicalBERT) processes the tokens through its neural network
3. **last_hidden_state** is the model's understanding of the text — a matrix of numbers
4. **.mean(dim=1)** averages it down to a single list of 768 numbers
5. That list IS the embedding

**`generate_answer()`** — The answer generation pipeline:
```python
def generate_answer(self, query, context_cases):
    # Try OpenAI first (best answers)
    if self.openai_client:
        return self._generate_openai_answer(query, context_cases)
    # Try ClinicalBERT QA (decent answers)
    if self.qa_pipeline:
        return self._generate_qa_answer(query, context_cases)
    # Fallback: just extract text snippets
    return self._generate_enhanced_answer(query, context_cases)
```

It tries the best method first, falls back if unavailable.

**`_generate_openai_answer()`** — Sends the retrieved cases to GPT:
```python
response = self.openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a medical AI assistant..."},
        {"role": "user", "content": f"Query: {query}\nCases: {context_text}"}
    ]
)
```

This is the "Generation" in RAG. GPT reads the cases and writes a coherent answer.

**`query_medical_cases()`** — The full pipeline:
```
User asks question
    → get_embedding(question)         # convert question to numbers
    → search_similar_cases(embedding) # find matching cases in database
    → generate_answer(question, cases) # GPT synthesizes an answer
    → return RAGResult                 # send back to user
```

#### e) Flask Web Interface (lines 1250+)

```python
app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # show login page, check username/password

@app.route('/api/medical_query', methods=['POST'])
def medical_query():
    # receive question from browser, run the RAG pipeline, return answer
```

**Flask** is a web framework. `@app.route('/login')` means "when someone visits `/login` in their browser, run this function." It's how the Python code becomes a website.

---

### 4. `test_query.py` — Testing the System

```python
session = requests.Session()                    # create a browser-like session
session.post(f'{base_url}/login', data=...)     # log in
response = session.post(f'{base_url}/api/medical_query', json={'query': '...'})
print(response.json()['answer'])                # print the answer
```

This simulates what happens when you use the website — it logs in, sends a question, and prints the answer. It's like testing a vending machine by putting in a coin and checking if the right snack comes out.

---

## The Full Flow (How It All Works Together)

```
You type: "What are symptoms of a heart attack?"
          ↓
    [ClinicalBERT] converts your question to 768 numbers
          ↓
    [Neon Database] compares those numbers against 1,682 case chunks
          ↓
    Returns 5 most similar cases (with full medical text)
          ↓
    [GPT-4o-mini] reads those 5 cases + your question
          ↓
    Writes a structured, cited medical answer
          ↓
    Displayed on the website
```

**ClinicalBERT** = the librarian who finds the right books
**GPT** = the doctor who reads them and explains it to you
**Neon** = the library where all the books are stored

---

---

# Neon Database — Deep Dive

---

## What is Neon?

**Neon** is a cloud-hosted PostgreSQL database. Think of it like Google Sheets, but instead of a spreadsheet:
- It's a **real database** that can handle millions of rows
- It lives **in the cloud** (not on your computer) — you connect over the internet
- It has a special plugin called **pgvector** that lets it store and compare embeddings (lists of numbers)

Your connection string in `.env`:
```
postgresql://neondb_owner:npg_GtLqMr0un3lS@ep-patient-mode-adyrdy4u-pooler...neon.tech/neondb
```
This is like an address + key:
- `neondb_owner` = your username
- `npg_GtLqMr0un3lS` = your password
- `ep-patient-mode-...neon.tech` = the server address
- `neondb` = the database name

---

## The `NeonRAGDatabase` Class — Method by Method

### 1. `connect()` — Opening the Connection

```python
def connect(self):
    self.conn = psycopg2.connect(self.connection_string)
    self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
    self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

**What it does**: Opens a connection to Neon, like dialing a phone number.

- `psycopg2.connect(...)` — Opens the connection using your connection string
- `cursor` — Think of this as your "hand" that writes and reads from the database. `RealDictCursor` means results come back as dictionaries (`{'case_id': 'case_001', 'content': '...'}`) instead of plain tuples
- `CREATE EXTENSION IF NOT EXISTS vector` — Turns on the pgvector plugin. This is like installing an app on the database that allows it to understand embeddings

---

### 2. `ensure_connection()` — Is the Line Still Open?

```python
def ensure_connection(self):
    if self.conn is None or self.conn.closed != 0:
        return self.connect()         # reconnect if dead
    with self.conn.cursor() as cur:
        cur.execute("SELECT 1")       # ping test
    return True
```

**What it does**: Checks if the connection is still alive. Cloud databases can drop connections if idle too long.

Think of it like checking if your phone call is still connected before speaking — if the line is dead, it redials.

---

### 3. `create_tables()` — Setting Up the Filing System

```python
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
```

**What it does**: Creates the table structure — like setting up columns in a spreadsheet.

| Column | Type | What it stores |
|---|---|---|
| `id` | SERIAL | Auto-incrementing row number (1, 2, 3...) |
| `case_id` | VARCHAR(255) | Name like `case_0445_mimic_chunk_3` |
| `content` | TEXT | The actual medical case text |
| `embedding` | vector(768) | 768 numbers from ClinicalBERT |
| `metadata` | JSONB | Extra info as JSON (flexible) |
| `created_at` | TIMESTAMP | When it was added |

The second table `query_history` saves every question anyone asks — useful for analytics.

Then it creates **indexes**:

```python
self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_embedding
    ON medical_cases USING ivfflat (embedding vector_cosine_ops)")
```

An **index** is like a book's index at the back — instead of reading every page to find "heart attack," you look it up in the index and jump to the right page. Without it, every query would scan all 1,682 rows. The `ivfflat` index groups similar embeddings into clusters so searches are fast.

---

### 4. `insert_medical_case()` — Saving a Case

```python
embedding_str = '[' + ','.join([str(float(x)) for x in case.embedding]) + ']'

self.cursor.execute("""
    INSERT INTO medical_cases (case_id, content, embedding, metadata)
    VALUES (%s, %s, %s::vector, %s)
    ON CONFLICT (case_id) DO UPDATE SET ...
""", (case.case_id, case.content, embedding_str, json.dumps(case.metadata)))
```

**What it does**: Saves one medical case into the database.

Step by step:
1. **Convert embedding to string** — Python has a list `[0.23, -0.15, 0.87]`, but PostgreSQL needs a string `'[0.23,-0.15,0.87]'`. The `::vector` part tells PostgreSQL "treat this string as a vector"
2. **INSERT** — Adds a new row to the table
3. **ON CONFLICT DO UPDATE** — If a case with the same `case_id` already exists, update it instead of failing. This prevents duplicate errors

Think of it like filling out a form and filing it in a cabinet. If the file already exists, you replace it with the updated version.

---

### 5. `search_similar_cases()` — THE MOST IMPORTANT METHOD

```python
embedding_str = '[' + ','.join([str(float(x)) for x in query_embedding]) + ']'

self.cursor.execute("""
    SELECT case_id, content, metadata,
           1 - (embedding <=> %s::vector) as similarity,
           embedding <=> %s::vector as distance
    FROM medical_cases
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT %s
""", (embedding_str, embedding_str, embedding_str, limit))
```

**This is where the magic happens.** Breaking down the SQL:

```sql
SELECT case_id, content, metadata,
```
"Give me the case ID, full text, and metadata..."

```sql
1 - (embedding <=> %s::vector) as similarity,
```
"...and calculate how similar each case is to my query."

The `<=>` operator is **cosine distance**. Here's the intuition:

Imagine two arrows pointing from the center of a circle:
- If they point in the **same direction** → distance = 0, similarity = 1 (perfect match)
- If they're at **90 degrees** → distance = 1, similarity = 0 (unrelated)
- If they point **opposite** → distance = 2, similarity = -1 (opposite meaning)

So `1 - distance = similarity`. Higher is better.

```sql
ORDER BY embedding <=> %s::vector
LIMIT 5
```
"Sort by distance (closest first) and give me only the top 5."

**Visual example**:

```
Your query: "heart attack symptoms"  →  [0.8, 0.3, -0.1, ...]

Database cases:
  case_0445 embedding: [0.79, 0.31, -0.12, ...]  → distance 0.14  → similarity 0.86  TOP MATCH
  case_0232 embedding: [0.75, 0.28, -0.09, ...]  → distance 0.17  → similarity 0.83
  case_0100 embedding: [0.10, 0.90,  0.50, ...]  → distance 0.78  → similarity 0.22  NOT SIMILAR
```

The **fallback query** (line 395-405) is a safety net — if the vector search crashes for any reason, it just grabs 5 random cases with a fake similarity of 0.5. Not ideal, but better than returning nothing.

---

### 6. `get_case_by_id()` — Looking Up a Specific Case

```python
# First try exact match
self.cursor.execute("SELECT ... WHERE case_id = %s", (case_id,))

# If no match, try partial match for chunked cases
self.cursor.execute("SELECT ... WHERE case_id LIKE %s", (f"{base_case_id}%",))
```

**What it does**: Looks up a specific case by name.

Why two tries? Because cases are split into chunks. If you search for `case_0445_mimic`, it might be stored as:
- `case_0445_mimic_chunk_1`
- `case_0445_mimic_chunk_2`
- `case_0445_mimic_chunk_3`

The `LIKE` query with `%` wildcard finds all chunks that start with that name.

---

### 7. `get_case_chunks_by_id()` — Get All Pieces of a Case

```python
self.cursor.execute("SELECT ... WHERE case_id LIKE %s ORDER BY case_id",
                     (f"{base_case_id}%",))
```

Same idea as above, but returns **all** chunks for a case, in order. This is used when you want to see the full case, not just the most relevant chunk.

---

### 8. `save_query_history()` — Keeping a Log

```python
self.cursor.execute("""
    INSERT INTO query_history (query, case_id, answer, confidence, processing_time)
    VALUES (%s, %s, %s, %s, %s)
""", (query, case_id, answer, confidence, processing_time))
```

Every time someone asks a question, it saves:
- What they asked
- What cases were used
- The answer generated
- How confident the system was
- How long it took

This is like keeping a log book — useful for seeing what questions people ask most, tracking performance, and debugging.

---

### 9. `get_system_stats()` — Dashboard Numbers

```sql
SELECT COUNT(*) as total_cases FROM medical_cases        -- how many cases?
SELECT COUNT(*) as total_queries FROM query_history      -- how many questions asked?
SELECT AVG(confidence) as avg_confidence FROM query_history  -- average confidence?
```

Simple dashboard stats. This powers the system statistics endpoint.

---

## The Full Data Flow

```
1. STARTUP:
   1,002 .txt case files in data/
       ↓
   ClinicalBERT converts each to 768 numbers (embedding)
       ↓
   insert_medical_case() saves text + embedding to Neon
       ↓
   1,682 chunks stored in cloud database (some cases split into multiple chunks)

2. QUERY TIME:
   User asks "What are heart attack symptoms?"
       ↓
   ClinicalBERT converts question to 768 numbers
       ↓
   search_similar_cases() sends those numbers to Neon
       ↓
   Neon compares against all 1,682 embeddings using cosine distance
       ↓
   Returns top 5 most similar cases (with full text + similarity score)
       ↓
   GPT reads those 5 cases and writes an answer
```

The Neon database is essentially a **smart filing cabinet** — you give it numbers, and it instantly finds the most similar files among thousands. That's what makes it a "vector database."

---

## Bugs That Were Fixed

1. **`LEFT(content, 200)` bug** — The SQL query was truncating all case content to 200 characters before passing it to answer generation. This meant GPT only saw tiny meaningless snippets instead of full medical cases. Fixed by returning full `content`.

2. **OpenAI GPT integration** — Added OpenAI as the primary answer generator. ClinicalBERT handles retrieval (embeddings + vector search), and GPT-4o-mini synthesizes coherent, structured medical answers from the retrieved cases.

3. **Hardcoded confidence (0.85)** — Confidence was always 0.85 regardless of actual similarity. Now calculated from real vector similarity scores returned by the database.

4. **`main()` function** — Required `OPENAI_API_KEY` but then never used OpenAI. Now properly integrates it for answer generation with a graceful warning if missing.
