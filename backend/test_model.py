import pandas as pd
import numpy as np
import faiss
import re
import ast
import os
import fitz                              # PyMuPDF, for PDFs
import pytesseract
from PIL import Image                    # For image inputs
from pdf2image import convert_from_path  # For scanned PDF OCR
from sentence_transformers import SentenceTransformer

# ----------------------------------------
# 1. LOAD MODEL
# ----------------------------------------
print("Step 1: Loading the trained model...")
model_dir = 'trained_legal_model_fixed'
assert os.path.exists(model_dir), "Model folder missing!"
model = SentenceTransformer(model_dir)
print("Model loaded successfully.\n")

# ----------------------------------------
# 2. LOAD CLAUSES
# ----------------------------------------
print("Step 2: Loading reference clauses from CSV...")
clauses_df = pd.read_csv('legal_clauses.csv')

def unwrap_clause(c):
    try:
        return ast.literal_eval(c)[0] if isinstance(c, str) and c.startswith("[") else c
    except:
        return c

clauses_df['Clause'] = clauses_df['Clause'].apply(unwrap_clause)
clauses = clauses_df['Clause'].tolist()
print(f"Loaded {len(clauses)} clauses.\n")

# ----------------------------------------
# 3. TEXT EXTRACTION LOGIC
# ----------------------------------------
def extract_text(file_path):
    if file_path.lower().endswith('.txt'):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif file_path.lower().endswith('.pdf'):
        try:
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            if len(text.strip()) < 50:
                return ocr_pdf_images(file_path)
            return text
        except Exception:
            return ocr_pdf_images(file_path)
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)
    else:
        raise ValueError("Unsupported file type. Use .txt, .pdf, .png, .jpg, .jpeg.")

def ocr_pdf_images(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

# -----
# Choose your file to process:
file_path = "legal document.pdf"  # <-- Change this to your TXT, PDF, or image filename!
test_text = extract_text(file_path)
print(f"Loaded document: {file_path}")
print(f"Sample (first 400 chars):\n{test_text[:400]}\n")
# -----

# ----------------------------------------
# 4. SPLIT DOCUMENT INTO CHUNKS
# ----------------------------------------
print("Step 4: Chunking document into sentences/paragraphs...")
chunks = [s.strip() for s in re.split(r'[\n\r.!?]', test_text) if len(s.strip()) > 20]
print(f"Found {len(chunks)} chunks.\n")

# ----------------------------------------
# 5. EMBED CHUNKS & FAISS INDEX
# ----------------------------------------
print("Step 5: Encoding document chunks...")
chunk_embeddings = model.encode(chunks, convert_to_tensor=False, show_progress_bar=True)
chunk_embeddings = np.array(chunk_embeddings).astype('float32')
faiss.normalize_L2(chunk_embeddings)
index = faiss.IndexFlatIP(chunk_embeddings.shape[1])
index.add(chunk_embeddings)
print("Chunks encoded and added to FAISS index.\n")

# ----------------------------------------
# 6. EMBED CLAUSES IN A BATCH & MATCH
# ----------------------------------------
print("Step 6: Encoding all clauses in a batch...")
clause_embeddings = model.encode(clauses, convert_to_tensor=False, show_progress_bar=True)
clause_embeddings = np.array(clause_embeddings).astype('float32')
faiss.normalize_L2(clause_embeddings)

print("Step 7: Matching clauses to document chunks (batched)...")
D, I = index.search(clause_embeddings, 3)  # top 3 matches per clause
results = []
for i, (distances, indices) in enumerate(zip(D, I)):
    clause = clauses[i]
    for idx, score in zip(indices, distances):
        if score > 0.75:
            results.append({
                "Clause": clause,
                "matched_text": chunks[idx],
                "similarity": float(score)
            })
print("Clause matching complete.\n")

results_df = pd.DataFrame(results)

# ----------------------------------------
# 7. ASSIGN RISK LEVELS & DOCUMENT SUMMARY
# ----------------------------------------
print("Step 8: Assigning risk levels and computing risk summary...")

def get_risk_label(score):
    if score <= 0.85:
        return "Low Risk"
    elif score <= 0.91:
        return "Medium Risk"
    else:
        return "High Risk"

if not results_df.empty:
    results_df["risk_level"] = results_df["similarity"].apply(get_risk_label)
    # Deduplicate: keep highest similarity match per unique chunk
    best_results = results_df.sort_values("similarity", ascending=False).drop_duplicates(subset=["matched_text"])
    # Risk counts
    risk_counts = best_results["risk_level"].value_counts().to_dict()
    low = risk_counts.get("Low Risk", 0)
    medium = risk_counts.get("Medium Risk", 0)
    high = risk_counts.get("High Risk", 0)
    # Overall document risk score
    weights = {"Low Risk": 0.5, "Medium Risk": 1.0, "High Risk": 1.0}
    weighted_sum = sum(row["similarity"] * weights[row["risk_level"]] for _, row in best_results.iterrows())
    total_weight = sum(weights[row["risk_level"]] for _, row in best_results.iterrows())
    avg_similarity = weighted_sum / total_weight if total_weight > 0 else 0.0
    doc_risk_level = get_risk_label(avg_similarity)
    # Print results
    print(f"\n========= Document Risk Summary =========")
    print(f"Weighted Document Risk Score: {avg_similarity:.4f}")
    print(f"Final Risk Level: {doc_risk_level}")
    print(f"Identified {len(best_results)} risky clause matches:")
    print(f"  • {low} Low Risk\n  • {medium} Medium Risk\n  • {high} High Risk\n")
    # Save to CSV
    best_results["document_risk_score"] = avg_similarity
    best_results["document_risk_level"] = doc_risk_level
    best_results.to_csv("risky_clause_matches.csv", index=False)
    print("Results saved to: risky_clause_matches.csv")
else:
    print("No matches found above threshold. No risk calculated.")
