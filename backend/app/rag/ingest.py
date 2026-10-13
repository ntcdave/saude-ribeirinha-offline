"""Ingestão: lê .txt/.md de data/docs -> chunks -> embeddings locais (Ollama) -> data/index.json.

TODO(equipe-dia): [PESSOA-DOCS] adicionar PDFs oficiais aqui. Dica: converta PDF p/ .txt
e rode `python scripts/build-index.py`. Não precisa mexer neste arquivo.
"""
import json
import sys
import requests
import numpy as np
from pathlib import Path

from app.rag.config import DOCS_DIR, INDEX_PATH, OLLAMA_URL, EMBED_MODEL
from app.rag.chunk import chunk_text


def embed_ollama(texts: list[str]) -> list[list[float]] | None:
    try:
        out: list[list[float]] = []
        for t in texts:
            r = requests.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": t},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            vec = data.get("embeddings", [data.get("embedding")])[0]
            out.append(vec)
        return out
    except Exception as e:
        print(f"[ingest] Ollama indisponível ({e}). Usando fallback sem vetores.", file=sys.stderr)
        return None


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([*DOCS_DIR.glob("*.txt"), *DOCS_DIR.glob("*.md")])
    if not files:
        print(f"[ingest] Nenhum documento em {DOCS_DIR}")
        return
    all_chunks: list[dict] = []
    for f in files:
        chunks = chunk_text(f.read_text(encoding="utf-8", errors="ignore"), f.name)
        all_chunks.extend(chunks)
    print(f"[ingest] {len(files)} docs -> {len(all_chunks)} chunks")

    vecs = embed_ollama([c["text"] for c in all_chunks])
    if vecs:
        arr = np.array(vecs, dtype=np.float32)
        # normaliza p/ busca cosseno rápida
        arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
        for c, v in zip(all_chunks, arr.tolist()):
            c["embedding"] = v
    INDEX_PATH.write_text(json.dumps({"chunks": all_chunks}, ensure_ascii=False), encoding="utf-8")
    print(f"[ingest] índice salvo em {INDEX_PATH} (com_vetores={bool(vecs)})")


if __name__ == "__main__":
    main()
