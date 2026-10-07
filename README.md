# VERITAS — Proof-Carrying Autonomous Data Analyst

## 1. What VERITAS is (Working System)
VERITAS is an AI-powered data analyst that allows a user to upload datasets and ask analytical questions in natural language. Unlike generic AI chatbots, VERITAS aims to provide analytical answers that are **computationally reproducible and verifiable**. It achieves this by writing, executing, and proving the validity of Python code against your actual data.

## 2. Core Model / Reasoning
VERITAS operates on a rigorous two-step reasoning mechanism powered by Large Language Models:
1. **The Planner (`AnalysisPlan`):** When a user asks a question, the LLM first generates a strict JSON `AnalysisPlan`. This plan maps the user's intent to specific columns, target metrics, operations (like aggregations or joins), and lists assumptions. 
2. **The Code Generator (`GeneratedAnalysisCode`):** The generated plan and the dataset profile are fed back into the LLM to generate deterministic, safe Python code.
3. **Local AI Native:** VERITAS currently runs 100% locally using **Ollama** and the `llama3.1` (8B) model, ensuring complete data privacy and removing external API dependencies or quotas.

## 3. Data Pipeline
1. **Data Collection (Upload):** Users upload `.csv`, `.xlsx`, or `.json` files via the React frontend.
2. **Data Profiling:** The FastAPI backend parses the data, extracting metadata like column names, data types, and sample rows (creating a `dataset_profile`).
3. **Data Passing:** The profile is passed to the LLM to understand the schema without viewing the full raw data.
4. **Secure Execution (Docker Sandbox):** The actual raw data is passed into an isolated, ephemeral Docker container (`veritas-sandbox`). The AI-generated code is executed securely inside this container against the data.
5. **Output Processing:** The resulting output (scalar, series, dataframe) is serialized and sent back to the frontend for visualization.

## 4. Evidence & Explanation
To prove how the system works and builds trust, VERITAS surfaces its entire internal thought process to the user interface:
- **Intermediate Outputs:** The UI displays the full AI-generated `AnalysisPlan` (showing intent, required columns, assumptions, and confidence scores).
- **Code Visibility:** The generated Python code is displayed directly to the user before and after execution.
- **Execution Traces:** Execution time (ms), rows returned, and a cryptographic SHA-256 hash of the executed code are provided as technical details to prove provenance.
- **Verification Engine:** An automated verification step checks the execution outputs against statistical anomalies.

## 5. Sample Input & Output
**Input Dataset:** `Order Details.csv` (contains 'Order ID', 'Amount', etc.)
**User Question:** *"total how many order"*
**System Process:**
- **Plan Generated:** Intent: `count`, Target Metric: `Order ID`
- **Code Generated:** 
  ```python
  import pandas as pd
  orders_csv = pd.read_csv('Order Details.csv')
  result = orders_csv['Order ID'].nunique()
  ```
**Output Displayed:** 
- Result Type: Scalar
- Value: `48` (Count of unique Order IDs)

## 6. Scope Note
- **Minimum Viable Solution:** 
  - File uploading and schema profiling.
  - LLM integration for intent planning and code generation.
  - Secure sandboxed execution using Docker.
  - Displaying results in the UI.
- **Stretch Goals Attempted:**
  - Complete local-LLM support (Ollama + llama3.1) for 100% privacy-preserving analysis without API limits.
  - Sandboxed execution architecture ensuring the host machine remains safe from arbitrary generated code.
  - Multi-dataset safe variable injection without uuid collision.

## 7. Setup & Run Instructions

### Prerequisites
- Python 3.11+
- Node.js & npm
- Docker (must be installed and running for the sandbox to execute code securely)
- Ollama (must be installed and running locally)

### Step 1: Start Ollama
Ensure you have pulled the `llama3.1` model:
```bash
ollama pull llama3.1
ollama serve
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Ensure your `backend/.env` file contains:
```
AI_PRIMARY_PROVIDER=ollama
AI_FALLBACK_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
```
Then start the server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 3: Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:5173`.
