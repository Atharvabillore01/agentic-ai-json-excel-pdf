from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from app.core.cache import cache

model = SentenceTransformer("all-MiniLM-L6-v2")

indexes = {}

def build_all_indexes():
    indexes.clear()

    for state, data in cache["states"].items():
        chunks = data.get("policy_chunks", [])
        if not chunks:
            continue

        texts = [c["text"] for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=True)

        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(np.array(embeddings))

        indexes[state] = index

def search_policy(query: str, state: str, k: int = 5):
    if state not in indexes:
        return []

    q_emb = model.encode([query])
    _, ids = indexes[state].search(q_emb, k)

    return [
        cache["states"][state]["policy_chunks"][i]
        for i in ids[0]
    ]
