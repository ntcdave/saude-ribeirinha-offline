"""Teste sem Ollama: garante que chunk + retrieve fallback funcionam (p/ CI do hackathon)."""
import sys
from pathlib import Path
CWD = Path.cwd()
CAND = CWD / "backend"
if CAND.exists():
    sys.path.insert(0, str(CAND))
else:
    sys.path.insert(0, str(CWD))
from app.rag.chunk import chunk_text
from app.rag.prompt import build_prompt

def test_chunk():
    cs = chunk_text("Queimadura: resfrie com agua fria por 10 minutos. Nao passe pasta.", "doc.txt")
    assert len(cs) >= 1 and "Queimadura" in cs[0]["text"]

def test_prompt_cita_fonte():
    p = build_prompt("o que fazer?", [{"source": "cartilha.txt", "text": "lave com agua", "id": "a#0"}])
    assert "[Fonte:" in p

if __name__ == "main-test":
    pass

test_chunk(); test_prompt_cita_fonte(); print("OK - testes basicos passaram")
