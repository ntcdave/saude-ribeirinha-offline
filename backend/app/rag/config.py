"""Config central do RAG + Ollama (Gemma 4, 100% local)."""
import os
from pathlib import Path

BASE_DIR = Path(os.getenv("BACKEND_DIR") or Path(__file__).resolve().parents[2])

DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
INDEX_PATH = DATA_DIR / "index.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemma4:e4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

TOP_K = int(os.getenv("TOP_K", "3"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

# Páginas a pular na ingestão (créditos/capa/contracapa/toc). Revisar com o owner.
SKIP_PAGES: dict[str, set[int]] = {
    "cartilha_tratamento_emergencia_queimaduras.pdf": {2},
    "nocoes_primeiros_socorros.pdf": {3, 5, 6, 7},
    "saude-guia-saude-ribeirinha_compressed.pdf": {3, 4},
    "trabalho_agente_comunitario_saude.pdf": {2, 3, 4},
}

CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "0.1"))
NUM_CTX = int(os.getenv("NUM_CTX", "4096"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))
KEEP_ALIVE = os.getenv("KEEP_ALIVE", "30m")

AVISO_SAUDE = (
    "Informacao educativa - nao substitui profissional de saude. "
    "Em emergencia, procure a UBS mais proxima ou ligue SAMU 192."
)

SOURCE_TITLES = {
    "cartilha_tratamento_emergencia_queimaduras.pdf": "Cartilha para Tratamento de Emergência das Queimaduras",
    "nocoes_primeiros_socorros.pdf": "Noções de Primeiros Socorros",
    "saude-guia-saude-ribeirinha_compressed.pdf": "Guia de Saúde Ribeirinha",
    "trabalho_agente_comunitario_saude.pdf": "O Trabalho do Agente Comunitário de Saúde",
}
