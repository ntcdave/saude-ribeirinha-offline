"""Busca local: cosseno com numpy se houver vetores, senão TF simples por palavras.

TODO(equipe-dia): [PESSOA-RAG] trocar por FAISS/Chroma se quiser. A interface
`retrieve(pergunta, k)` não muda, então o resto do app continua igual.
"""
import json
import re
import requests
import numpy as np

from .config import INDEX_PATH, OLLAMA_URL, EMBED_MODEL, TOP_K

_WORD = re.compile(r"[a-zà-ú0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


def _load():
    if not INDEX_PATH.exists():
        return []
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))["chunks"]


def _embed_query(q: str):
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": q}, timeout=30
        )
        r.raise_for_status()
        data = r.json()
        v = np.array(data.get("embeddings", [data.get("embedding")])[0], dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)
    except Exception:
        return None


def retrieve(pergunta: str, k: int = TOP_K) -> list[dict]:
    chunks = _load()
    if not chunks:
        return []
    # 1) tenta vetorial
    if chunks[0].get("embedding"):
        q = _embed_query(pergunta)
        if q is not None:
            mat = np.array([c["embedding"] for c in chunks], dtype=np.float32)
            scores = mat @ q
            idx = np.argsort(-scores)[:k]
            return [chunks[int(i)] for i in idx]
    # 2) fallback léxico (funciona até sem Ollama — bom p/ demo/teste)
    qt = _tokens(pergunta)
    scored = sorted(chunks, key=lambda c: len(qt & _tokens(c["text"])), reverse=True)
    return scored[:k]
