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
from transformers import pipeline
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

print(">>> Loading summarization model...")
try:
    summarizer = pipeline(
        "summarization", 
        model="facebook/bart-large-cnn",
        device=-1
    )
    print(">>> Summarizer loaded successfully.")
except Exception as e:
    print(f">>> Warning: Could not load summarizer - {str(e)}")
    summarizer = None

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

def extract_text_with_locations(file_path):
    """
    Extract text from PDF/TXT with page numbers and line numbers
    Returns: (full_text, text_segments)
    text_segments = [{text, page, line}, ...]
    """
    print("...Extracting text with location data from", file_path)
    
    text_segments = []
    full_text = ""
    
    if file_path.lower().endswith('.txt'):
        # TXT file processing
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line_num, line_text in enumerate(lines, start=1):
                if line_text.strip():
                    text_segments.append({
                        'text': line_text.strip(),
                        'page': 1,  # TXT files are single page
                        'line': line_num
                    })
                    full_text += line_text
        
        return full_text, text_segments
    
    elif file_path.lower().endswith('.pdf'):
        try:
            # PDF file processing with PyMuPDF
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    page_text = page.get_text()
                    
                    if len(page_text.strip()) < 50:
                        # Try OCR if text extraction fails (skip here; summarizer handles if needed)
                        print(f"... Page {page_num} has little text, trying OCR")
                        continue
                    
                    # Split page text into lines
                    lines = page_text.split('\n')
                    line_num = 1
                    
                    for line_text in lines:
                        if line_text.strip() and len(line_text.strip()) > 10:
                            text_segments.append({
                                'text': line_text.strip(),
                                'page': page_num,
                                'line': line_num
                            })
                            full_text += line_text + "\n"
                            line_num += 1
            
            return full_text, text_segments
            
        except Exception as e:
            print(f"... Exception in PDF processing: {str(e)}")
            # Fallback to simple extraction
            return extract_text(file_path), []
    
    else:
        # Fallback for other formats
        return extract_text(file_path), []

def get_risk_label(score):
    if score <= 0.85:
        return "Low Risk"
    elif score <= 0.91:
        return "Medium Risk"
    else:
        return "High Risk"

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Enhanced analysis that returns risky clauses WITH their locations
    """
    try:
        print(">>> [API] Received request with location tracking")
        file = request.files['file']
        file_path = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        file.save(file_path)
        print(f">>> [API] Saved file to {file_path}")

        # Extract text with location information
        test_text, text_segments = extract_text_with_locations(file_path)
        print(f">>> [API] Extracted {len(text_segments)} text segments with locations")

        # Create chunks with location mapping
        chunks_with_locations = []
        for segment in text_segments:
            # Split long segments into sentences
            sentences = re.split(r'[.!?]', segment['text'])
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 20:
                    chunks_with_locations.append({
                        'text': sent,
                        'page': segment['page'],
                        'line': segment['line']
                    })
        
        chunks = [item['text'] for item in chunks_with_locations]
        print(">>> [API] Number of text chunks:", len(chunks))

        if not chunks:
            return jsonify({"error": "No valid content found in document"}), 400

        # Encode document chunks
        print(">>> [API] Encoding document chunks ...")
        chunk_embeddings = model.encode(chunks, convert_to_tensor=False, batch_size=32)
        chunk_embeddings = np.array(chunk_embeddings, dtype='float32')
        faiss.normalize_L2(chunk_embeddings)
        index = faiss.IndexFlatIP(chunk_embeddings.shape[1])
        index.add(chunk_embeddings)
        print(">>> [API] Document chunk embeddings completed.")

        # Run FAISS similarity search
        print(">>> [API] Running FAISS similarity search ...")
        D, I = index.search(clause_embeddings, 3)
        print(">>> [API] Similarity search complete.")

        # Collect results with locations
        results = []
        for i, (distances, indices) in enumerate(zip(D, I)):
            clause = clauses[i]
            for idx, score in zip(indices, distances):
                if score > 0.75:
                    location_info = chunks_with_locations[idx]
                    results.append({
                        "Clause": clause,
                        "matched_text": location_info['text'],
                        "similarity": float(score),
                        "page": location_info['page'],
                        "line": location_info['line']
                    })
        
        results_df = pd.DataFrame(results)
        print(f">>> [API] Number of matches above threshold: {len(results_df)}")

        risky_clause_locations = []
        if not results_df.empty:
            results_df["risk_level"] = results_df["similarity"].apply(get_risk_label)
            best_results = results_df.sort_values("similarity", ascending=False).drop_duplicates(subset=["matched_text"])
            
            # Extract location information for risky clauses
            for _, row in best_results.iterrows():
                risky_clause_locations.append({
                    "text": row["matched_text"][:100] + "..." if len(row["matched_text"]) > 100 else row["matched_text"],
                    "page": int(row["page"]),
                    "line": int(row["line"]),
                    "risk_level": row["risk_level"],
                    "similarity": float(row["similarity"])
                })
            
            risk_counts = best_results["risk_level"].value_counts().to_dict()
            low = risk_counts.get("Low Risk", 0)
            medium = risk_counts.get("Medium Risk", 0)
            high = risk_counts.get("High Risk", 0)
            
            weights = {"Low Risk": 0.5, "Medium Risk": 1.0, "High Risk": 1.0}
            weighted_sum = sum(row["similarity"] * weights[row["risk_level"]] for _, row in best_results.iterrows())
            total_weight = sum(weights[row["risk_level"]] for _, row in best_results.iterrows())
            avg_similarity = weighted_sum / total_weight if total_weight > 0 else 0.0
            doc_risk_level = get_risk_label(avg_similarity)

            # (NEW) do NOT create the old CSV anymore; if it exists, remove it.
            old_csv = os.path.join("uploads", "risky_clause_matches.csv")
            try:
                if os.path.exists(old_csv):
                    os.remove(old_csv)
                    print(f">>> Removed old CSV {old_csv}")
            except Exception as e:
                print(">>> Could not remove old CSV:", str(e))

            summary = {
                "low_risk": low,
                "medium_risk": medium,
                "high_risk": high,
                "document_risk_score": avg_similarity,
                "document_risk_level": doc_risk_level,
                "risky_clause_locations": risky_clause_locations
            }
        else:
            summary = {
                "low_risk": 0,
                "medium_risk": 0,
                "high_risk": 0,
                "document_risk_score": 0.0,
                "document_risk_level": "Low Risk",
                "risky_clause_locations": []
            }
        
        return jsonify(summary)
    except Exception as e:
        print(">>> [API] Exception occurred:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/summarize', methods=['POST'])
def summarize_document():
    """
    Generate document summary AND identify risky clause locations
    """
    try:
        print(">>> [SUMMARIZE] Received summarization request")
        
        if summarizer is None:
            return jsonify({
                "error": "Summarization model not available"
            }), 500
        
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        file_path = os.path.join("uploads", f"temp_summary_{file.filename}")
        os.makedirs("uploads", exist_ok=True)
        file.save(file_path)
        print(f">>> [SUMMARIZE] Saved file to {file_path}")
        
        # STEP 1: Extract text with locations
        full_text, text_segments = extract_text_with_locations(file_path)
        print(f">>> [SUMMARIZE] Extracted {len(full_text)} characters from {len(text_segments)} segments")
        
        if len(full_text.strip()) < 100:
            return jsonify({
                "error": "Document too short to summarize"
            }), 400
        
        # STEP 2: Generate document summary
        print(">>> [SUMMARIZE] Generating content summary...")
        max_chunk_size = 1200
        words = full_text.split()
        chunk_size_words = max_chunk_size // 5
        
        chunk_texts = []
        for i in range(0, len(words), chunk_size_words):
            chunk = ' '.join(words[i:i + chunk_size_words])
            if len(chunk) > 200:
                chunk_texts.append(chunk)
        
        chunk_texts = chunk_texts[:5]  # Limit to first 5 chunks
        
        summaries = []
        for idx, chunk in enumerate(chunk_texts):
            try:
                print(f">>> [SUMMARIZE] Processing chunk {idx + 1}/{len(chunk_texts)}")
                summary_result = summarizer(
                    chunk,
                    max_length=180,
                    min_length=40,
                    do_sample=False,
                    truncation=True
                )
                summaries.append(summary_result[0]['summary_text'])
            except Exception as e:
                print(f">>> [SUMMARIZE] Error in chunk {idx}: {str(e)}")
                continue
        
        if not summaries:
            return jsonify({"error": "Could not generate summary"}), 500
        
        content_summary = " ".join(summaries)
        
        # STEP 3: Identify risky clauses with locations
        print(">>> [SUMMARIZE] Identifying risky clauses...")
        
        # Create chunks with location mapping
        chunks_with_locations = []
        for segment in text_segments:
            sentences = re.split(r'[.!?]', segment['text'])
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 20:
                    chunks_with_locations.append({
                        'text': sent,
                        'page': segment['page'],
                        'line': segment['line']
                    })
        
        chunks = [item['text'] for item in chunks_with_locations]
        
        if chunks:
            # Encode chunks
            chunk_embeddings = model.encode(chunks, convert_to_tensor=False, batch_size=32)
            chunk_embeddings = np.array(chunk_embeddings, dtype='float32')
            faiss.normalize_L2(chunk_embeddings)
            index = faiss.IndexFlatIP(chunk_embeddings.shape[1])
            index.add(chunk_embeddings)
            
            # Search for risky clauses
            D, I = index.search(clause_embeddings, 3)
            
            # Collect risky clause locations
            risky_locations = []
            seen_locations = set()
            
            for i, (distances, indices) in enumerate(zip(D, I)):
                clause = clauses[i]
                for idx, score in zip(indices, distances):
                    if score > 0.75:  # Risky threshold
                        location_info = chunks_with_locations[idx]
                        location_key = (location_info['page'], location_info['line'])
                        
                        # Avoid duplicates
                        if location_key not in seen_locations:
                            seen_locations.add(location_key)
                            
                            risk_level = get_risk_label(score)
                            matched_text = location_info['text']
                            
                            risky_locations.append({
                                "text": matched_text[:80] + "..." if len(matched_text) > 80 else matched_text,
                                "full_text": matched_text,
                                "page": location_info['page'],
                                "line": location_info['line'],
                                "risk_level": risk_level,
                                "similarity": float(score),
                                "matched_clause": clause[:100] + "..." if len(clause) > 100 else clause
                            })
            
            # Sort by page and line
            risky_locations.sort(key=lambda x: (x['page'], x['line']))
            
            risky_locations = risky_locations[:100]
        else:
            risky_locations = []
        
        print(f">>> [SUMMARIZE] Found {len(risky_locations)} risky clause locations")
        
        # --- Save new CSV of clause locations (page, line, matched_text, matched_clause, risk_level, similarity)
        try:
            clauses_csv_path = os.path.join("uploads", "risky_clause_locations.csv")

            if risky_locations:
                rows = []
                for rl in risky_locations:
                    rows.append({
                        "page": int(rl.get("page", 0)),
                        "line": int(rl.get("line", 0)),
                        "matched_text": rl.get("full_text", rl.get("text", "")),
                        "matched_clause": rl.get("matched_clause", ""),
                        "risk_level": rl.get("risk_level", ""),
                        "similarity": float(rl.get("similarity", 0.0))
                    })
                df_clauses = pd.DataFrame(
                    rows, 
                    columns=["page", "line", "matched_text", "matched_clause", "risk_level", "similarity"]
                )
                df_clauses.to_csv(clauses_csv_path, index=False)
                print(f">>> [SUMMARIZE] Saved clauses CSV to {clauses_csv_path}")
            else:
                if os.path.exists(os.path.join("uploads", "risky_clause_locations.csv")):
                    os.remove(os.path.join("uploads", "risky_clause_locations.csv"))
                    print(">>> [SUMMARIZE] Removed stale clause CSV (none found in this run).")
        except Exception as e:
            print(">>> [SUMMARIZE] Could not save clauses CSV:", str(e))

        # STEP 4: Calculate statistics
        original_length = len(full_text)
        summary_length = len(content_summary)
        compression_ratio = round((summary_length / original_length) * 100, 2)
        
        # Group locations by page for easy reference
        locations_by_page = {}
        for loc in risky_locations:
            page = loc['page']
            if page not in locations_by_page:
                locations_by_page[page] = []
            locations_by_page[page].append({
                "line": loc['line'],
                "risk_level": loc['risk_level'],
                "text": loc['text']
            })
        
        # Clean up temp file
        try:
            os.remove(file_path)
        except:
            pass
        
        print(">>> [SUMMARIZE] Summary generation complete")
        
        return jsonify({
            "content_summary": content_summary,
            "risky_clause_locations": risky_locations,
            "locations_by_page": locations_by_page,
            "total_risky_clauses": len(risky_locations),
            "original_length": original_length,
            "summary_length": summary_length,
            "compression_ratio": compression_ratio,
            "chunks_processed": len(summaries)
        })
        
    except Exception as e:
        print(f">>> [SUMMARIZE] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# NEW: serve the new clauses CSV (page+line+texts)
@app.route('/download_clauses', methods=['GET'])
def download_clauses_csv():
    try:
        save_path = os.path.join("uploads", "risky_clause_locations.csv")
        if os.path.exists(save_path):
            print(f">>> [API] Serving clauses CSV {save_path}")
            return send_file(save_path, as_attachment=True)
        else:
            print(">>> [API] Clauses CSV not found.")
            return jsonify({"error": "No clauses results file found."}), 404
    except Exception as e:
        print(">>> [API] Exception in download_clauses endpoint:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(">>> Starting Flask on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
