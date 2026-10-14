from app.rag.emergency import detect_emergency

def test_emergency():
    assert detect_emergency("meu filho desmaiou") == "desmaiou"
    assert detect_emergency("como lavar as mãos") is None

def test_accents_casing():
    assert detect_emergency("DESMAIOU") is not None
    assert detect_emergency("Convulsão") is not None