from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from app.core.cache import cache
import logging

logger = logging.getLogger(__name__)

model = SentenceTransformer("all-MiniLM-L6-v2")

indexes = {}


def build_all_indexes():
    """Build vector indexes for all states with enhanced metadata"""
    indexes.clear()

    for state, data in cache["states"].items():
        chunks = data.get("policy_chunks", [])
        if not chunks:
            logger.warning(f"No policy chunks for state: {state}")
            continue

        texts = [c.get("text", "") for c in chunks if c.get("text")]
        
        if not texts:
            logger.warning(f"No valid text in policy chunks for state: {state}")
            continue

        logger.info(f"Building index for {state} with {len(texts)} chunks")
        
        try:
            embeddings = model.encode(texts, show_progress_bar=False)

            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(np.array(embeddings, dtype=np.float32))

            indexes[state] = {
                "index": index,
                "chunks": chunks,
                "texts": texts
            }
            
            logger.info(f"Index built for {state}")
        except Exception as e:
            logger.error(f"Error building index for {state}: {e}")


def search_policy(query: str, state: str, k: int = 5) -> list:
    """
    Search policies with enhanced result ranking.
    
    Args:
        query: Search query
        state: State to search in
        k: Number of results to return
    
    Returns:
        List of relevant policy chunks with metadata
    """
    if state not in indexes:
        logger.warning(f"No index available for state: {state}")
        return []

    state_index = indexes[state]
    chunks = state_index["chunks"]
    index = state_index["index"]
    
    # Handle empty query
    if not query or not query.strip():
        return chunks[:k]
    
    try:
        # Encode query
        q_emb = model.encode([query.strip()], show_progress_bar=False)
        
        # Search with L2 distance
        distances, ids = index.search(np.array(q_emb, dtype=np.float32), min(k * 2, len(chunks)))
        
        # Rank by relevance (lower distance = higher relevance)
        results = []
        for idx in ids[0]:
            if idx >= 0 and idx < len(chunks):  # Ensure valid index
                chunk = chunks[int(idx)].copy()
                results.append(chunk)
        
        # Return top k
        return results[:k]
    
    except Exception as e:
        logger.error(f"Error searching policies for state {state}: {e}")
        return []


def search_policies_multi_state(query: str, states: list, k: int = 5) -> dict:
    """
    Search across multiple states.
    
    Returns:
        Dictionary mapping state to results
    """
    results = {}
    for state in states:
        results[state] = search_policy(query, state, k)
    return results
