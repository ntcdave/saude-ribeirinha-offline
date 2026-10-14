"""Divide textos em chunks com overlap. Simples de propósito: fácil de explicar no pitch."""
from .config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, source: str) -> list[dict]:
    text = text.strip().replace("\r\n", "\n")
    chunks: list[dict] = []
    start = 0
    i = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        # tenta quebrar em fim de frase/parágrafo
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if cut > start + 200:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append({"id": f"{source}#{i}", "source": source, "text": piece, "start": start})
            i += 1
        start = end - CHUNK_OVERLAP
        if start < 0:
            start = 0
        if end >= len(text):
            break
    return chunks
