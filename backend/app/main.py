"""API FastAPI: /api/health + /api/ask. Serve o frontend estático junto (uso em 1 clique).

Respostas SEMPRE via Gemma 4 (CHAT_MODEL) — sem modo demo, sem modelo reserva.
Se o Ollama estiver fora do ar, /api/ask responde 502 em vez de inventar conteúdo.
"""
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.rag.config import (
    BASE_DIR, OLLAMA_URL, CHAT_MODEL, AVISO_SAUDE, CHAT_TEMPERATURE, NUM_CTX, OLLAMA_TIMEOUT, KEEP_ALIVE,
)
from app.rag.retrieve import retrieve
from app.rag.prompt import build_prompt, parse_card
from app.rag.emergency import detect_emergency

app = FastAPI(title="Saude Ribeirinha Offline (Gemma 4 + RAG local)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AskIn(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)
    k: int = Field(default=3, ge=1, le=5)

    @field_validator("pergunta", mode="before")
    @classmethod
    def _strip(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v
def _chat(prompt: str) -> str:
    # Único modelo de resposta: Gemma 4. Qualquer falha vira exceção (sem reserva, sem demo).
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": CHAT_TEMPERATURE, "num_ctx": NUM_CTX},
            "keep_alive": KEEP_ALIVE,
        },
        timeout=OLLAMA_TIMEOUT,
    )
    r.raise_for_status()
    return (r.json().get("response") or "").strip()

@app.get("/api/health")
@app.get("/health")
def health():
    return {"ok": True, "model": CHAT_MODEL, "aviso": AVISO_SAUDE}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/api/lan-url")
def lan_url(request: Request):
    import socket
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = None
    if not ip:
        host = request.headers.get("host", "")
        ip = host.split(":")[0] if host else "localhost"
    port = request.url.port or 8000
    if ":" in (request.headers.get("host","")):
        try:
            port = int(request.headers.get("host","").split(":")[1])
        except Exception:
            pass
    return {"url": f"http://{ip}:{port}/#chat"}

@app.post("/api/ask")
def ask(body: AskIn):
    alerta_flag = detect_emergency(body.pergunta)
    alerta = None
    if alerta_flag:
        alerta = {
            "motivo": alerta_flag,
            "titulo": "EMERGÊNCIA",
            "mensagem": "Acione o rádio comunitário ou disque SAMU 192 (ligação gratuita).",
        }

    def _fallback_emergencia():
        return {
            "resposta": "",
            "fontes": [],
            "trechos": [],
            "modo": "emergencia-estatico",
            "alerta": alerta,
            "card": {"tipo": "emergencia", "titulo": "EMERGÊNCIA", "icone": "emergency", "passos": [], "fonte": "", "aviso": AVISO_SAUDE},
        }

    trechos = retrieve(body.pergunta, k=body.k)
    if not trechos:
        if alerta:
            return _fallback_emergencia()
        raise HTTPException(status_code=404, detail="Ainda nao tenho documentos indexados. Rode python scripts/build-index.py. " + AVISO_SAUDE)
    prompt = build_prompt(body.pergunta, trechos)
    fontes_raw = [{"source": t["source"], "id": t["id"], "page": t.get("page")} for t in trechos]
    seen_src = set()
    fontes = []
    for f in fontes_raw:
        if f["source"] in seen_src:
            continue
        seen_src.add(f["source"])
        fontes.append(f)
    try:
        resp = _chat(prompt)
    except Exception as e:
        if alerta:
            return _fallback_emergencia()
        raise HTTPException(status_code=502, detail=f"Ollama indisponivel ({CHAT_MODEL} em {OLLAMA_URL}). Verifique se o Ollama esta rodando com o modelo {CHAT_MODEL}.") from e
    if not resp:
        if alerta:
            return _fallback_emergencia()
        raise HTTPException(status_code=502, detail="O modelo nao retornou resposta. Tente novamente.")
    card = parse_card(resp, body.pergunta, fontes)
    if card.get("tipo") == "sem_resposta":
        out = {"resposta": resp, "fontes": [], "modo": "gemma4-rag", "trechos": [], "card": card}
        if alerta:
            out["alerta"] = alerta
        return out
    out = {"resposta": resp, "fontes": fontes, "modo": "gemma4-rag", "trechos": trechos, "card": card}
    if alerta:
        out["alerta"] = alerta
    return out

FRONT = BASE_DIR.parent / "frontend"
if FRONT.exists():
    app.mount("/", StaticFiles(directory=str(FRONT), html=True), name="frontend")
