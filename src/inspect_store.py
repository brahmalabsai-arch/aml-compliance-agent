"""
inspect.py — See what's actually inside your RAG vector store.

Two modes:
  python src/inspect.py            -> lists every chunk that was stored
  python src/inspect.py "your question here"  -> shows what gets retrieved

This is how you verify your chunking + retrieval without touching the web app.
"""
import sys
import os
import chromadb
from chromadb.utils import embedding_functions

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION = "aml_policies"


def get_collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection(COLLECTION, embedding_function=embed_fn)


def list_all_chunks():
    col = get_collection()
    data = col.get()  # returns every stored item
    print(f"\nTotal chunks stored: {len(data['ids'])}\n" + "=" * 70)
    for i, (cid, doc, meta) in enumerate(
        zip(data["ids"], data["documents"], data["metadatas"])
    ):
        print(f"\n[CHUNK {i}]  id={cid}")
        print(f"  source : {meta['source']}")
        print(f"  section: {meta['section']}")
        print(f"  length : {len(doc)} chars")
        print("  ---")
        # print first 5 lines of the chunk so you can eyeball it
        for line in doc.splitlines()[:6]:
            print(f"  {line}")
        if len(doc.splitlines()) > 6:
            print("  ...")


def test_retrieval(query, k=3):
    col = get_collection()
    res = col.query(query_texts=[query], n_results=k)
    print(f"\nQUERY: {query}\n" + "=" * 70)
    for rank, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), 1
    ):
        print(f"\n#{rank}  distance={dist:.4f}  (lower = closer match)")
        print(f"     {meta['source']} -> {meta['section']}")
        print("     ---")
        for line in doc.splitlines()[:5]:
            print(f"     {line}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_retrieval(" ".join(sys.argv[1:]))
    else:
        list_all_chunks()
