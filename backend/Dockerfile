# Use a slim, modern Python image for a small and fast container
FROM python:3.11-slim

WORKDIR /app

# Only copy requirements, then install to optimize Docker build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only needed application files (add more .py files as needed)
COPY app.py .
COPY legal_clauses.csv .

# Start Flask app with Gunicorn (production-grade web server)
CMD ["gunicorn", "app:app"]
