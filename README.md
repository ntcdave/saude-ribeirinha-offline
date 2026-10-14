# Saude Ribeirinha Offline 🌿
Assistente de saude basica e primeiros socorros **100% offline, em portugues**, para comunidades ribeirinhas e indigenas da Amazonia.

Roda com **Gemma 4 (open-weight, Google)** via **Ollama local** + **RAG local** sobre cartilhas oficiais. Nenhum dado sai do notebook. Sem chave de API, sem internet no uso.

Feito para o **Hacktoberfest Hack Day Rio Branco (LASI x UFAC) — premio "Best Open-Source AI Project"**.

## Por que importa (Acre)
- Internet ruim ou nula no interior; posto longe; duvida simples vira emergencia.
- Resposta com **citacao da fonte** `[Fonte: ...]`, linguagem simples, e aviso fixo: *nao substitui profissional; emergencia SAMU 192*.
- Se nao esta nos documentos, diz que nao sabe — nao inventa.

## Como rodar (Windows, 5 min)
1. `powershell -ExecutionPolicy Bypass -File scripts/setup-ollama.ps1` (instala Ollama + `gemma4:e4b` + `nomic-embed-text`)
2. `powershell -ExecutionPolicy Bypass -File scripts/run-dev.ps1`
3. Abra `http://localhost:8000` → pergunte. Desligue o Wi-Fi e pergunte de novo (prova do offline).

Manual:
```
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ..\scripts\build-index.py
python -m uvicorn app.main:app --reload --port 8000
```

## Arquitetura
```
pergunta → retrieve() [hibrido: vetor Ollama nomic-embed-text + lexico] → build_prompt() → ollama generate gemma4:e4b → card padrao + fontes
```
- `backend/app/main.py` — API `/api/health`, `/api/ask`, serve frontend.
- `backend/app/rag/` — `ingest.py`, `retrieve.py`, `prompt.py`, `chunk.py`, `config.py`.
- `frontend/` — chat HTML puro (sem build).
- `backend/data/docs/` — coloque `.txt` oficiais aqui e rode build-index.

## Divisao p/ equipe nova (ver docs/EQUIPE-DIVISAO.md)
- UI/voz, Docs/RAG, Backend/demo, Pitch. Tudo marcado com `TODO(equipe-dia)` no codigo.

## Teste rapido sem Ollama
`python tests/test_rag.py` — valida chunk + prompt.

## Licenca
MIT — uso livre, inclusive comercial. Ver LICENSE.
