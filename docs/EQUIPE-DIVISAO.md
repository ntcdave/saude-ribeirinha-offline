# Divisao p/ equipe de 2-4 pessoas montada na hora (cole no quadro)

## Pessoa 1 — voce (backend + demo) [já pronto]
- Garantir `ollama list` mostra `gemma4:e4b`. Rodar build-index. Testar `/api/ask`.

## Pessoa 2 — UI [iniciante-friendly, so frontend/]
- Melhorar `styles.css`, adicionar botao limpar, modo alto-contraste.
- Extra: gravar audio com MediaRecorder. Arquivo: `frontend/app.js` (tem TODO).

## Pessoa 3 — Docs/RAG [impacto alto no jurado]
- Trocar os 2 `.txt` demo por trechos reais de cartilhas oficiais (cite a fonte no nome do arquivo).
- Rodar `python scripts/build-index.py` e testar 5 perguntas. Arquivos: `backend/data/docs/`.

## Pessoa 4 — Pitch + teste [decide o premio]
- Ensaiar roteiro `docs/PITCH-3MIN.md`. Filmar demo com Wi-Fi desligado.
- Rodar `python tests/test_rag.py` antes de subir no palco.

Regra: ninguem quebra o `main`. Commits pequenos, `git pull` sempre.
