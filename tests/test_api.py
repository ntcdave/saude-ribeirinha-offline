import app.main as M
from fastapi.testclient import TestClient

def test_validation(small_index, chat_ok):
    client = TestClient(M.app)
    r = client.post("/api/ask", json={"pergunta": ""})
    assert r.status_code == 422
    r = client.post("/api/ask", json={"pergunta": "a"*600})
    assert r.status_code == 422

def test_404_no_index(tmp_path, monkeypatch):
    import app.rag.config as cfg
    import app.rag.retrieve as ret
    p = tmp_path/"index.json"
    monkeypatch.setattr(cfg, "INDEX_PATH", p)
    monkeypatch.setattr(ret, "INDEX_PATH", p)
    ret._IDX["mtime"]=None
    ret._CACHE["n"]=-1
    client = TestClient(M.app)
    r = client.post("/api/ask", json={"pergunta": "pergunta valida"})
    assert r.status_code == 404

def test_502_ollama_down(small_index):
    import app.main as main
    def boom(prompt):
        raise ConnectionError("down")
    main._chat = boom
    client = TestClient(main.app)
    r = client.post("/api/ask", json={"pergunta": "pergunta valida"})
    assert r.status_code == 502

def test_emergency_ollama_down(small_index):
    import app.main as main
    def boom(prompt):
        raise ConnectionError("down")
    main._chat = boom
    client = TestClient(main.app)
    r = client.post("/api/ask", json={"pergunta": "meu filho desmaiou"})
    assert r.status_code == 200
    d = r.json()
    assert d["alerta"] is not None
    assert d["card"]["tipo"] == "emergencia"

def test_refusal_empty_fontes(small_index, chat_ok):
    # make chat return refusal
    import app.main as main
    def refusal(prompt):
        return "Não encontrei isso nos documentos oficiais que tenho aqui."
    main._chat = refusal
    client = TestClient(main.app)
    r = client.post("/api/ask", json={"pergunta": "algo"})
    assert r.status_code == 200
    d = r.json()
    assert d["card"]["tipo"] == "sem_resposta"
    assert d["fontes"] == []
    assert d["trechos"] == []