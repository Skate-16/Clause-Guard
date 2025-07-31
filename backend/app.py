from flask import Flask, request, jsonify, send_file
import pandas as pd
import numpy as np
import faiss
import re
import ast
import os
import fitz
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from sentence_transformers import SentenceTransformer
from flask_cors import CORS

from huggingface_hub import snapshot_download
from dotenv import load_dotenv
import os

load_dotenv() 
HF_TOKEN = os.getenv("HF_TOKEN")

print(">>> Downloading model folder from Hugging Face Hub ...")
model_dir = snapshot_download(
    repo_id="Skate-16/Clause-Guard",    
    use_auth_token=HF_TOKEN
)
print(">>> Downloaded model to:", model_dir)
print(">>> Loading SentenceTransformer model ...")
model = SentenceTransformer(model_dir)
print(">>> Model loaded.")

app = Flask(__name__)

frontend_url = os.getenv("FRONTEND_URL")               
origins = ["http://localhost:4200"]
if frontend_url:
    origins.append(frontend_url)
CORS(app, origins=origins)

print(">>> Reading clauses from CSV ...")
clauses_df = pd.read_csv('legal_clauses.csv')  

def unwrap_clause(c):
    try:
        return ast.literal_eval(c)[0] if isinstance(c, str) and c.startswith("[") else c
    except:
        return c
clauses_df['Clause'] = clauses_df['Clause'].apply(unwrap_clause)
clauses = clauses_df['Clause'].tolist()
print(f">>> Loaded {len(clauses)} clauses.")

print("Embedding reference clauses ...")
clause_embeddings = model.encode(clauses, convert_to_tensor=False, batch_size=32)
clause_embeddings = np.array(clause_embeddings, dtype='float32')
faiss.normalize_L2(clause_embeddings)
print("Clause embeddings ready.")

def extract_text(file_path):
    print("...Extracting text from", file_path)
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
        except Exception as e:
            print("... Exception in PyMuPDF, trying OCR fallback:", str(e))
            return ocr_pdf_images(file_path)
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)
    else:
        raise ValueError("Unsupported file type. Use .txt, .pdf, .png, .jpg, .jpeg.")

def ocr_pdf_images(pdf_path):
    print("...Doing OCR on scanned PDF images ...")
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print(">>> [API] Received request")
        file = request.files['file']
        file_path = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        file.save(file_path)
        print(f">>> [API] Saved file to {file_path}")

        test_text = extract_text(file_path)
        print(f">>> [API] Extracted text length: {len(test_text)} chars")

        chunks = [s.strip() for s in re.split(r'[\n\r.!?]', test_text) if len(s.strip()) > 20]
        print(">>> [API] Number of text chunks:", len(chunks))

        if not chunks:
            print(">>> [API] No valid chunks found.")
            return jsonify({"error": "No valid content found in document"}), 400

        print(">>> [API] Encoding document chunks ...")
        chunk_embeddings = model.encode(chunks, convert_to_tensor=False, batch_size=32)
        chunk_embeddings = np.array(chunk_embeddings, dtype='float32')
        faiss.normalize_L2(chunk_embeddings)
        index = faiss.IndexFlatIP(chunk_embeddings.shape[1])
        index.add(chunk_embeddings)
        print(">>> [API] Document chunk embeddings completed.")

        print(">>> [API] Running FAISS similarity search ...")
        D, I = index.search(clause_embeddings, 3)
        print(">>> [API] Similarity search complete.")

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
        results_df = pd.DataFrame(results)
        print(f">>> [API] Number of matches above threshold: {len(results_df)}")

        def get_risk_label(score):
            if score <= 0.85:
                return "Low Risk"
            elif score <= 0.91:
                return "Medium Risk"
            else:
                return "High Risk"

        summary = {}
        if not results_df.empty:
            results_df["risk_level"] = results_df["similarity"].apply(get_risk_label)
            best_results = results_df.sort_values("similarity", ascending=False).drop_duplicates(subset=["matched_text"])
            risk_counts = best_results["risk_level"].value_counts().to_dict()
            low = risk_counts.get("Low Risk", 0)
            medium = risk_counts.get("Medium Risk", 0)
            high = risk_counts.get("High Risk", 0)
            weights = {"Low Risk": 0.5, "Medium Risk": 1.0, "High Risk": 1.0}
            weighted_sum = sum(row["similarity"] * weights[row["risk_level"]] for _, row in best_results.iterrows())
            total_weight = sum(weights[row["risk_level"]] for _, row in best_results.iterrows())
            avg_similarity = weighted_sum / total_weight if total_weight > 0 else 0.0
            doc_risk_level = get_risk_label(avg_similarity)
            best_results["document_risk_score"] = avg_similarity
            best_results["document_risk_level"] = doc_risk_level
            save_path = os.path.join("uploads", "risky_clause_matches.csv")
            best_results.to_csv(save_path, index=False)
            print(f">>> [API] Results saved to {save_path}")

            summary = {
                "low_risk": low,
                "medium_risk": medium,
                "high_risk": high,
                "document_risk_score": avg_similarity,
                "document_risk_level": doc_risk_level
            }
        else:
            print(">>> [API] No matches found above threshold.")
            summary = {
                "low_risk": 0,
                "medium_risk": 0,
                "high_risk": 0,
                "document_risk_score": 0.0,
                "document_risk_level": "Low Risk"
            }
        print(">>> [API] Returning JSON summary.")
        return jsonify(summary)
    except Exception as e:
        print(">>> [API] Exception occurred:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['GET'])
def download_csv():
    try:
        save_path = os.path.join("uploads", "risky_clause_matches.csv")
        if os.path.exists(save_path):
            print(f">>> [API] Serving CSV {save_path}")
            return send_file(save_path, as_attachment=True)
        else:
            print(">>> [API] CSV not found.")
            return jsonify({"error": "No results file found."}), 404
    except Exception as e:
        print(">>> [API] Exception in download endpoint:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(">>> Starting Flask on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
