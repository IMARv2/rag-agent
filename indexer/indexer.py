import hashlib
from pathlib import Path
from typing import List
import httpx
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.chroma import get_collection
from indexer.parsers import parse_file
from config import settings

SUPPORTED_EXTS = {".pdf", ".txt", ".md", ".rst", ".csv"}

def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def _chunk_text(text: str) -> List[str]:
    size, overlap = settings.chunk_size, settings.chunk_overlap
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]

def _embed(text: str) -> List[float]:
    r = httpx.post(
        f"{settings.ollama_base_url}/api/embed",
        json={"model": settings.embed_model, "input": text},
        timeout=60
    )
    r.raise_for_status()
    return r.json()["embeddings"][0]

def index_file(path: str) -> dict:
    collection = get_collection()
    file_hash = _file_hash(path)
    rel_path = str(Path(path).relative_to(settings.docs_path))

    existing = collection.get(where={"source": rel_path}, include=["metadatas"])
    if existing["ids"] and existing["metadatas"][0].get("hash") == file_hash:
        return {"status": "skipped", "path": rel_path}
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    text = parse_file(path)
    if not text.strip():
        return {"status": "empty", "path": rel_path}

    chunks = _chunk_text(text)
    ids, embeddings, documents, metadatas = [], [], [], []
    for i, chunk in enumerate(chunks):
        ids.append(f"{rel_path}::{i}")
        embeddings.append(_embed(chunk))
        documents.append(chunk)
        metadatas.append({
            "source": rel_path,
            "hash": file_hash,
            "chunk": i,
            "total_chunks": len(chunks),
            "ext": Path(path).suffix.lower()
        })

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return {"status": "indexed", "path": rel_path, "chunks": len(chunks)}

def index_all() -> dict:
    results = []
    for p in Path(settings.docs_path).rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            try:
                results.append(index_file(str(p)))
            except Exception as e:
                results.append({"status": "error", "path": str(p), "error": str(e)})
    return {"total": len(results), "results": results}


def delete_file(rel_path: str) -> dict:
    """Remove all chunks of a file from ChromaDB by relative path."""
    collection = get_collection()
    existing = collection.get(where={"source": rel_path}, include=["metadatas"])
    if not existing["ids"]:
        return {"status": "not_found", "path": rel_path}
    collection.delete(ids=existing["ids"])
    return {"status": "deleted", "path": rel_path, "chunks": len(existing["ids"])}

def sync_index() -> dict:
    """Remove ChromaDB entries for files no longer on disk."""
    collection = get_collection()
    if collection.count() == 0:
        return {"removed": 0}
    all_meta = collection.get(include=["metadatas"])
    sources = set(m["source"] for m in all_meta["metadatas"])
    removed = 0
    for rel_path in sources:
        full_path = str(Path(settings.docs_path) / rel_path)
        if not Path(full_path).exists():
            result = delete_file(rel_path)
            removed += result.get("chunks", 0)
    return {"removed": removed}

def search_docs(query: str, top_k: int = None) -> List[dict]:
    collection = get_collection()
    top_k = top_k or settings.top_k
    results = collection.query(
        query_embeddings=[_embed(query)],
        n_results=min(top_k, max(collection.count(), 1)),
        include=["documents", "metadatas", "distances"]
    )
    output = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        output.append({
            "content": doc,
            "source": meta["source"],
            "chunk": meta["chunk"],
            "score": round(1 - dist, 4)
        })
    return output
