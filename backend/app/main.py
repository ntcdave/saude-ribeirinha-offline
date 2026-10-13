"""API FastAPI: /api/health + /api/ask. Serve o frontend junto p/ demo em 1 clique.

TODO(equipe-dia):
 - [PESSOA-BACKEND] adicionar POST /api/docs (upload de .txt) se der tempo.
 - [PESSOA-VOZ] adicionar POST /api/stt usando audio do Gemma 4 e4b.
"""
from pathlib import Path
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag.config import OLLAMA_URL, CHAT_MODEL, CHAT_MODEL_FALLBACK, AVISO_SAUDE
from app.rag.retrieve import retrieve
from app.rag.prompt import build_prompt

app = FastAPI(title="Saude Ribeirinha Offline (Gemma 4 + RAG local)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AskIn(BaseModel):
    pergunta: str
    k: int = 3

def _chat(prompt: str, model: str):
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=180)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception:
        return None

@app.get("/api/health")
def health():
    return {"ok": True, "model": CHAT_MODEL, "fallback": CHAT_MODEL_FALLBACK, "aviso": AVISO_SAUDE}

@app.post("/api/ask")
def ask(body: AskIn):
    trechos = retrieve(body.pergunta, k=body.k)
    if not trechos:
        return {"resposta": "Ainda nao tenho documentos indexados. Rode python scripts/build-index.py. " + AVISO_SAUDE, "fontes": [], "modo": "sem-indice"}
    prompt = build_prompt(body.pergunta, trechos)
    resp = _chat(prompt, CHAT_MODEL) or _chat(prompt, CHAT_MODEL_FALLBACK)
    if resp:
        return {"resposta": resp, "fontes": [{"source": t["source"], "id": t["id"]} for t in trechos], "modo": "gemma4-rag", "trechos": trechos}
    bullets = "\n".join("- " + t["text"][:300] + " [Fonte: " + t["source"] + "]" for t in trechos)
    return {"resposta": "(modo demo sem Ollama) Encontrei isto:\n" + bullets + "\n\n" + AVISO_SAUDE, "fontes": [{"source": t["source"], "id": t["id"]} for t in trechos], "modo": "demo-sem-ollama", "trechos": trechos}

# Serve o chat estatico: detecta frontend/ a partir do cwd (sem dunder).
CWD = Path.cwd()
if (CWD / "frontend").exists():
    FRONT = CWD / "frontend"
elif (CWD / ".." / "frontend").exists():
    FRONT = (CWD / ".." / "frontend").resolve()
elif ((CWD / "backend").exists()):
    FRONT = CWD / "frontend"
else:
    FRONT = Path("frontend")
# raiz do projeto tem frontend/; backend roda com cwd=backend/ -> sobe um nivel
if not FRONT.exists() and CWD.name == "backend":
    FRONT = CWD.parent / "frontend"
if FRONT.exists():
    app.mount("/", StaticFiles(directory=str(FRONT), html=True), name="frontend")
