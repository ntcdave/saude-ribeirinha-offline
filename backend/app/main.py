"""API FastAPI: /api/health + /api/ask. Serve o frontend estático junto (uso em 1 clique).

Respostas SEMPRE via Gemma 4 (CHAT_MODEL) — sem modo demo, sem modelo reserva.
Se o Ollama estiver fora do ar, /api/ask responde 502 em vez de inventar conteúdo.
"""
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag.config import OLLAMA_URL, CHAT_MODEL, AVISO_SAUDE
from app.rag.retrieve import retrieve
from app.rag.prompt import build_prompt, parse_card

app = FastAPI(title="Saude Ribeirinha Offline (Gemma 4 + RAG local)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AskIn(BaseModel):
    pergunta: str
    k: int = 3

def _chat(prompt: str) -> str:
    # Único modelo de resposta: Gemma 4. Qualquer falha vira exceção (sem reserva, sem demo).
    r = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": CHAT_MODEL, "prompt": prompt, "stream": False}, timeout=180)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()

@app.get("/api/health")
@app.get("/health")
def health():
    return {"ok": True, "model": CHAT_MODEL, "aviso": AVISO_SAUDE}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.post("/api/ask")
def ask(body: AskIn):
    trechos = retrieve(body.pergunta, k=body.k)
    if not trechos:
        raise HTTPException(status_code=404, detail="Ainda nao tenho documentos indexados. Rode python scripts/build-index.py. " + AVISO_SAUDE)
    prompt = build_prompt(body.pergunta, trechos)
    fontes = [{"source": t["source"], "id": t["id"]} for t in trechos]
    try:
        resp = _chat(prompt)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama indisponivel ({CHAT_MODEL} em {OLLAMA_URL}). Verifique se o Ollama esta rodando com o modelo {CHAT_MODEL}.") from e
    if not resp:
        raise HTTPException(status_code=502, detail="O modelo nao retornou resposta. Tente novamente.")
    return {"resposta": resp, "fontes": fontes, "modo": "gemma4-rag", "trechos": trechos, "card": parse_card(resp, body.pergunta, fontes)}

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
