"""Ingestão: lê .txt/.md/.pdf de data/docs -> chunks -> embeddings locais (Ollama) -> data/index.json.

É só jogar o PDF em data/docs e rodar `python scripts/build-index.py`.
TODO(equipe-dia): [PESSOA-DOCS] continuar adicionando cartilhas oficiais aqui.
"""
import json
import sys
import hashlib
import bisect
import re
import requests
import numpy as np
from pathlib import Path

from app.rag.config import DOCS_DIR, INDEX_PATH, OLLAMA_URL, EMBED_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, SKIP_PAGES
from app.rag.chunk import chunk_text

BATCH = 32


def clean_text(s: str) -> str:
    # Junta palavras hifenizadas na quebra de linha.
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s or "")
    out_lines = []
    for line in s.splitlines():
        if re.fullmatch(r"\s*\d+\s*", line):
            # linha contendo apenas número de página
            continue
        out_lines.append(line)
    s = "\n".join(out_lines)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def read_pdf(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    out = []
    for idx, page in enumerate(reader.pages, 1):
        try:
            out.append((idx, page.extract_text() or ""))
        except Exception:
            out.append((idx, ""))
    return out


def read_doc(path: Path) -> list[tuple[int, str]]:
    if path.suffix.lower() == ".pdf":
        return read_pdf(path)
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        txt = ""
    return [(1, txt)]


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
        raise RuntimeError(f"[ingest] Ollama indisponivel ({e}). Suba o Ollama com '{EMBED_MODEL}' e rode de novo.") from e


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_emb(vecs):
    arr = np.array(vecs, dtype=np.float32)
    arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
    return arr.tolist()


def main(force: bool = False) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([*DOCS_DIR.glob("*.txt"), *DOCS_DIR.glob("*.md"), *DOCS_DIR.glob("*.pdf")])
    files = [f for f in files if f.name != "SOURCES.md"]
    if not files:
        print(f"[ingest] Nenhum documento em {DOCS_DIR}")
        return

    # Load existing index (if any) for incremental build.
    existing_data = {}
    if INDEX_PATH.exists() and not force:
        try:
            existing_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing_data = {}
    existing_docs = existing_data.get("docs", {}) if isinstance(existing_data, dict) else {}
    existing_chunks = existing_data.get("chunks", []) if isinstance(existing_data, dict) else []
    existing_chunks_by_id = {c.get("id"): c for c in existing_chunks if isinstance(c, dict)}
    existing_settings = existing_data.get("settings", {}) if isinstance(existing_data, dict) else {}
    new_settings = {"embed_model": EMBED_MODEL, "chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP}
    settings_changed = force or existing_settings != new_settings

    all_chunks: list[dict] = []
    docs_meta: dict[str, dict] = {}
    changed_texts: list[str] = []
    changed_refs: list[dict] = []  # chunks needing embedding

    for f in files:
        sha = sha256_file(f)
        doc_changed = force or settings_changed or existing_docs.get(f.name, {}).get("sha256") != sha
        if not doc_changed:
            # Reuse existing chunks.
            ids = existing_docs.get(f.name, {}).get("chunk_ids", [])
            reused = 0
            for cid in ids:
                c = existing_chunks_by_id.get(cid)
                if c is not None:
                    all_chunks.append(json.loads(json.dumps(c)))
                    reused += 1
            print(f"[ingest] {f.name}: sem mudanças ({reused} chunks reutilizados)")
            docs_meta[f.name] = {"sha256": sha, "chunk_ids": list(ids)}
            continue
        try:
            pages = read_doc(f)
        except Exception as e:
            print(f"[ingest] pulando {f.name}: {e}", file=sys.stderr)
            continue
        skip = SKIP_PAGES.get(f.name, set())
        # Build cleaned full text with page offsets.
        parts: list[str] = []
        page_offsets: list[tuple[int, int]] = []
        pos = 0
        for pnum, raw in pages:
            if pnum in skip:
                continue
            ct = clean_text(raw)
            if not ct.strip():
                continue
            if parts:
                parts.append("\n")
                pos += 1
            page_offsets.append((pos, pnum))
            parts.append(ct)
            pos += len(ct)
        text = "".join(parts)
        if not text.strip():
            print(f"[ingest] vazio (scaneado? precisa OCR): {f.name}", file=sys.stderr)
            continue
        # Map offset -> page using bisect.
        offsets = [po[0] for po in page_offsets]

        def _page_for(start: int) -> int | None:
            idx = bisect.bisect_right(offsets, start) - 1
            if idx < 0:
                return None
            return page_offsets[idx][1]

        chunks = chunk_text(text, f.name)
        for c in chunks:
            c["page"] = _page_for(c.get("start", 0))
        print(f"[ingest] {f.name}: {len(chunks)} chunks")
        chunk_ids = [c["id"] for c in chunks]
        docs_meta[f.name] = {"sha256": sha, "chunk_ids": chunk_ids}
        for c in chunks:
            if "embedding" not in c or not c.get("embedding"):
                changed_texts.append(c["text"])
                changed_refs.append(c)
        all_chunks.extend(chunks)

    # Embed changed chunks.
    if changed_texts:
        vecs = embed_ollama(changed_texts)
        if vecs:
            arr = _normalize_emb(vecs)
            for c, v in zip(changed_refs, arr):
                c["embedding"] = v

    INDEX_PATH.write_text(
        json.dumps(
            {"version": 2, "settings": new_settings, "docs": docs_meta, "chunks": all_chunks},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[ingest] índice salvo em {INDEX_PATH} (total={len(all_chunks)})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    main(force=args.force)