import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import json
import pytest

@pytest.fixture
def small_index(tmp_path, monkeypatch):
    import app.rag.config as cfg
    import app.rag.retrieve as ret
    idx_path = tmp_path / "index.json"
    chunks = [
        {"id": "burn#0", "source": "cartilha_tratamento_emergencia_queimaduras.pdf", "text": "Queimou na brasa do fogao: resfrie com agua fria", "page": 1},
        {"id": "burn#1", "source": "cartilha_tratamento_emergencia_queimaduras.pdf", "text": "Nao passe pasta de dente. Nao estoure bolhas.", "page": 2},
        {"id": "snake#0", "source": "nocoes_primeiros_socorros.pdf", "text": "Picada de cobra: lave com agua e sabao", "page": 3},
        {"id": "water#0", "source": "saude-guia-saude-ribeirinha_compressed.pdf", "text": "Para agua potavel use cloro e ferva", "page": 4},
        {"id": "dengue#0", "source": "trabalho_agente_comunitario_saude.pdf", "text": "Dengue febre e mosquito Aedes", "page": 5},
        {"id": "other#0", "source": "nocoes_primeiros_socorros.pdf", "text": "Diarreia soro reidratacao", "page": 6},
    ]
    idx_path.write_text(json.dumps({"version": 2, "settings": {}, "docs": {}, "chunks": chunks}), encoding="utf-8")
    monkeypatch.setattr(cfg, "INDEX_PATH", idx_path)
    monkeypatch.setattr(ret, "INDEX_PATH", idx_path)
    monkeypatch.setattr(ret, "_embed_query", lambda q: None)
    # invalidate caches
    ret._IDX["mtime"] = None
    ret._CACHE["n"] = -1
    return idx_path

@pytest.fixture
def chat_ok(monkeypatch):
    import app.main as main
    def fake(prompt):
        return "TITULO: T\nPASSO 1: A | B\nPASSO 2: C | D\nFONTE: cartilha_tratamento_emergencia_queimaduras.pdf"
    monkeypatch.setattr(main, "_chat", fake)
    return fake