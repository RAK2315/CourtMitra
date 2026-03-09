import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import hashlib
import os

VECTOR_STORE_PATH = os.path.join(os.path.dirname(__file__), "../vectorstore")
EMBED_MODEL = "all-MiniLM-L6-v2"

_model = None
_client = None
_collection = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
        _collection = _client.get_or_create_collection(
            name="courtmitra_judgments",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def embed_chunks(chunks: List[Dict], doc_name: str) -> int:
    """Embed and store chunks in ChromaDB. Returns number of chunks stored."""
    model = get_model()
    collection = get_collection()

    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    ids = []
    metadatas = []
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{doc_name}_{i}_{chunk['content'][:50]}".encode()).hexdigest()
        ids.append(chunk_id)
        metadatas.append({
            "doc_name": doc_name,
            "section": chunk["section"],
            "index": chunk["index"],
        })

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(chunks)


def retrieve_similar(query: str, top_k: int = 5, doc_name: str = None) -> List[Dict]:
    """Retrieve top-k similar chunks for a query."""
    model = get_model()
    collection = get_collection()

    query_embedding = model.encode([query]).tolist()

    where = {"doc_name": doc_name} if doc_name else None

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count() or 1),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "content": doc,
                "section": meta.get("section", ""),
                "doc_name": meta.get("doc_name", ""),
                "similarity": round(1 - dist, 3),
            })
    return output


def find_similar_cases(query_text: str, exclude_doc: str = None, top_k: int = 3) -> List[Dict]:
    """Find similar cases from the vector store, excluding the current document."""
    model = get_model()
    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = model.encode([query_text]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(20, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    seen_docs = set()
    similar_cases = []

    if results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            doc_name = meta.get("doc_name", "")
            if doc_name != exclude_doc and doc_name not in seen_docs:
                seen_docs.add(doc_name)
                similar_cases.append({
                    "doc_name": doc_name,
                    "similarity": round(1 - dist, 3),
                    "excerpt": doc[:200] + "...",
                })
                if len(similar_cases) >= top_k:
                    break

    return similar_cases


def list_indexed_documents() -> List[str]:
    """List all documents currently in the vector store."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.get(include=["metadatas"])
    docs = set()
    for meta in results["metadatas"]:
        docs.add(meta.get("doc_name", ""))
    return sorted(list(docs))
