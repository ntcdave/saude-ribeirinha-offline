"""Config central do RAG + Ollama (Gemma 4, 100% local). Sem dunder file (compat)."""
import os
from pathlib import Path

CWD = Path.cwd()
# roda de backend/ ou da raiz — detecta sozinho
if (CWD / "app" / "rag").exists():
    BASE_DIR = CWD
elif (CWD / "backend" / "app").exists():
    BASE_DIR = CWD / "backend"
else:
    BASE_DIR = Path(os.getenv("BACKEND_DIR", str(CWD / "backend"))).resolve()

DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
INDEX_PATH = DATA_DIR / "index.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemma4:e4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

TOP_K = int(os.getenv("TOP_K", "3"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

AVISO_SAUDE = (
    "Informacao educativa - nao substitui profissional de saude. "
    "Em emergencia, procure a UBS mais proxima ou ligue SAMU 192."
)
