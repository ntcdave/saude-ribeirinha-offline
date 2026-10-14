import app.rag.prompt as P

def test_refusal_basic():
    txt = "Não encontrei isso nos documentos oficiais que tenho aqui. Procure um agente de saúde/UBS."
    card = P.parse_card(txt, "pergunta", [])
    assert card["tipo"] == "sem_resposta"
    assert card["fonte"] == ""
    assert card["passos"] == []

def test_refusal_accents_and_extra():
    txt = "Xyz. NAO ENCONTREI ISSO NOS DOCUMENTOS oficiais... mais texto."
    card = P.parse_card(txt, "q", [])
    assert card["tipo"] == "sem_resposta"

    txt2 = "não encontrei isso nos documentos e tal"
    assert P.is_refusal(txt2)

def test_variable_steps_no_padding():
    resp = "TITULO: T\nPASSO 1: A | B\nPASSO 2: C | D\nFONTE: f.pdf"
    card = P.parse_card(resp, "q", [{"source":"f.pdf"}])
    assert len(card["passos"]) == 2
    assert all(p["destaque"] != "Procure ajuda presencial" for p in card["passos"])

def test_five_steps():
    resp = "TITULO: T\n" + "\n".join(f"PASSO {i}: A{i} | B{i}" for i in range(1,6)) + "\nFONTE: f.pdf"
    card = P.parse_card(resp, "q", [{"source":"f.pdf"}])
    assert len(card["passos"]) == 5

def test_title_regex_no_cross():
    txt = "TITULO:\nPASSO 1: a | b\nFONTE: f.pdf"
    card = P.parse_card(txt, "q", [{"source":"f.pdf"}])
    assert card["titulo"] not in ("PASSO 1: a | b",) and "PASSO 1" not in card["titulo"]

def test_source_validation():
    fontes = [{"source": "real.pdf"}]
    resp = "TITULO: T\nPASSO 1: A | B\nFONTE: inventado.pdf"
    card = P.parse_card(resp, "q", fontes)
    assert card["fonte"] == "real.pdf"
    assert card.get("fonte_corrigida") is True

def test_markdown_cleanup():
    resp = "TITULO: **T**\nPASSO 1: A | B\nFONTE: f.pdf"
    card = P.parse_card(resp, "q", [{"source":"f.pdf"}])
    assert "*" not in card["titulo"]