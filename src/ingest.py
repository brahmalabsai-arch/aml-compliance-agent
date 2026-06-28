"""
ingest.py — Build the RAG vector store from the policy documents in data/.

Run once before agent.py. Re-run whenever you change the documents.
"""
import os
import glob
import chromadb
from chromadb.utils import embedding_functions

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION = "aml_policies"


def chunk_by_section(text, source):
    """Split a markdown policy doc into chunks at '## Section' boundaries.
    Policy clauses are self-contained, so section-level chunks retrieve cleanly."""
    chunks, current, header = [], [], None
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                chunks.append((header, "\n".join(current)))
            header, current = line[3:].strip(), [line]
        else:
            current.append(line)
    if current:
        chunks.append((header, "\n".join(current)))
    return [
        {"id": f"{source}::{i}", "text": body, "source": source, "section": hdr}
        for i, (hdr, body) in enumerate(chunks)
        if body.strip() and hdr is not None
    ]


def main():
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # Reset collection so re-runs are idempotent
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, embedding_function=embed_fn)

    all_chunks = []
    for path in glob.glob(os.path.join(DATA_DIR, "*.md")):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        all_chunks.extend(chunk_by_section(text, os.path.basename(path)))

    col.add(
        ids=[c["id"] for c in all_chunks],
        documents=[c["text"] for c in all_chunks],
        metadatas=[{"source": c["source"], "section": c["section"]} for c in all_chunks],
    )
    print(f"Ingested {len(all_chunks)} chunks into '{COLLECTION}'.")


if __name__ == "__main__":
    main()
