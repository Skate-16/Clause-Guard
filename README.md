# Clause-Guard: Legal Document Risk Analyzer

1. What This Project Is About
- Clause-Guard is an AI-driven legal risk analysis system that helps professionals automatically detect risky clauses in legal documents (contracts, agreements, policies).
- Legal documents often contain clauses that may be:
  - Unfair (e.g., “Termination without notice”)
  - Ambiguous (e.g., “at the discretion of the company”)
  - Risk-heavy (e.g., “Unlimited liability”)
  - Restrictive (e.g., strict non-compete agreements)
- Traditional approach: Lawyers and compliance officers manually read hundreds of pages → time-consuming, error-prone, costly.
- Clause-Guard approach:
  - Uses LegalBERT + SBERT for risky pattern detection.
  - Compares text against curated dataset (legal_clauses.csv).
  - Assigns a risk score (0–100) to documents.
  - Upload via Angular frontend → results with visuals + CSV export.
- Model Hosting: Trained LegalBERT+SBERT model (~400 MB) hosted on Hugging Face Hub. Flask backend downloads it if not found locally.
- In short: Clause-Guard transforms manual review → AI-powered, efficient, and data-driven risk analysis.

2. Features
- Document Handling
  - Upload .txt, .pdf, and scanned images.
  - PyPDF2 → extract text from PDFs.
  - Tesseract OCR → read scanned PDFs/images.
- Risky Clause Detection (AI-powered)
  - LegalBERT → embeddings trained on case law, statutes, contracts.
  - SBERT (Sentence-BERT) → semantic similarity, not just keywords.
  - Hybrid model → catches rephrased risky clauses too.
- FAISS-Powered Fast Search
  - FAISS index built from risky clause embeddings.
  - Uploaded doc sentences compared against FAISS index.
  - Near real-time detection.
- Risk Scoring & Analysis
  - Each clause → similarity score (0–1).
  - Severity weights → reflect importance.
  - Overall risk score (0–100) for the document.
  - Output includes: risky clauses, similarity scores, severity labels (Low, Medium, High), and overall risk score.
- Web Interface (Angular Frontend)
  - File upload UI → backend analysis.
  - Risky clauses displayed with highlights.
  - Interactive charts for risk distribution.
  - CSV export option.
  - Runs on http://localhost:4200 during development.
- Deployment Flexibility
  - Local: Model in backend/trained_legal_model_fixed/.
  - Cloud: Model hosted on Hugging Face.
  - Frontend: Angular app deployable to Vercel, Netlify, Firebase Hosting.

3. How We Implemented The Features
- Backend (Flask + Python)
  - REST API (/upload) handles file uploads.
  - Text extraction: .txt → direct read, .pdf → PyPDF2, images → Tesseract OCR.
  - Model inference: LegalBERT+SBERT encodes sentences into embeddings.
  - Risk matching: FAISS index compares doc sentences against risky clause database.
  - Risk scoring: similarity thresholds + severity weights → JSON response with risky clauses and document risk score.
- Frontend (Angular)
  - UI/UX: File upload form.
  - API integration: Calls Flask backend.
  - Results display: Risky clauses in tables, risk distribution via Chart.js/Recharts, CSV export option.
  - Built with Angular CLI 19.2.9.
- Hugging Face Integration
  - Model hosted on Hugging Face Hub.
  - Backend logic: load local model if present, else pull from Hugging Face.
  - Bypasses GitHub storage limits, works in cloud deployments.
- Workflow Example
  1. User uploads contract (PDF).
  2. Backend extracts text → splits into sentences.
  3. Sentences → embeddings → compared with FAISS index.
  4. Similar clauses flagged with risk labels.
  5. JSON response → risky clauses + scores.
  6. Angular frontend → shows results visually + CSV export.

4. How To Run This App On Your Device

Backend Setup:
# Clone repo
git clone https://github.com/Skate-16/Clause-Guard
cd Clause-Guard/backend

# Setup virtual environment
python -m venv venv

# Activate venv (Windows example)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# PowerShell
.\venv\Scripts\Activate.ps1
# or Command Prompt
venv\Scripts\activate
# or Bash/Linux/Mac
source venv/Scripts/activate

# Install requirements
pip install -r requirements.txt

# Run backend
python app.py

Backend starts at: http://127.0.0.1:5000

Frontend Setup:
cd ../frontend
npm install
ng serve

Frontend starts at: http://localhost:4200

Connecting Backend & Frontend:
- Run both servers.
- Angular frontend calls Flask API (http://127.0.0.1:5000).
- Update frontend/src/environments/environment.ts if backend deployed separately.

Extra Angular Commands:
# Generate new component
ng generate component component-name

# Build project
ng build

# Run unit tests
ng test

# Run end-to-end tests
ng e2e

Now open http://localhost:4200 → Upload a document → View analysis → Download results.
