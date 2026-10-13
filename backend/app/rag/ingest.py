"""Ingestão: lê .txt/.md/.pdf de data/docs -> chunks -> embeddings locais (Ollama) -> data/index.json.

É só jogar o PDF em data/docs e rodar `python scripts/build-index.py`.
TODO(equipe-dia): [PESSOA-DOCS] continuar adicionando cartilhas oficiais aqui.
"""
import json
import sys
import requests
import numpy as np
from pathlib import Path

from app.rag.config import DOCS_DIR, INDEX_PATH, OLLAMA_URL, EMBED_MODEL
from app.rag.chunk import chunk_text

BATCH = 32


def read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)


def read_doc(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def _embed_batch(batch: list[str]) -> list[list[float]]:
    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": batch},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    if "embeddings" in data:
        return data["embeddings"]
    return [data["embedding"]]


def embed_ollama(texts: list[str]) -> list[list[float]] | None:
    try:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            out.extend(_embed_batch(texts[i:i + BATCH]))
            print(f"[ingest] embeddings {min(i + BATCH, len(texts))}/{len(texts)}", flush=True)
        return out
    except Exception as e:
        print(f"[ingest] Ollama indisponível ({e}). Usando fallback sem vetores.", file=sys.stderr)
        return None


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([*DOCS_DIR.glob("*.txt"), *DOCS_DIR.glob("*.md"), *DOCS_DIR.glob("*.pdf")])
    if not files:
        print(f"[ingest] Nenhum documento em {DOCS_DIR}")
        return
    all_chunks: list[dict] = []
    for f in files:
        try:
            text = read_doc(f)
        except Exception as e:
            print(f"[ingest] pulando {f.name}: {e}", file=sys.stderr)
            continue
        if not text.strip():
            print(f"[ingest] vazio (scaneado? precisa OCR): {f.name}", file=sys.stderr)
            continue
        chunks = chunk_text(text, f.name)
        print(f"[ingest] {f.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)
    print(f"[ingest] total: {len(files)} docs -> {len(all_chunks)} chunks")

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
