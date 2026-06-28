# ---- AML Compliance Agent: containerized FastAPI service ----
# Build:  docker build -t compliance-agent .
# Run:    docker run -p 8000:8000 --env-file .env compliance-agent
# Then open http://127.0.0.1:8000/docs

FROM python:3.12-slim

# Keep Python lean and logs unbuffered (so container logs stream live)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (this layer is cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Build the vector store at image-build time so the container is ready to serve.
# (Pre-downloads the embedding model and ingests data/ into chroma_db/.)
RUN python src/ingest.py

EXPOSE 8000

# Serve the FastAPI app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
