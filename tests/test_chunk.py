from app.rag.chunk import chunk_text

def test_basic():
    cs = chunk_text("Queimadura: resfrie com agua fria por 10 minutos. Nao passe pasta.", "doc.txt")
    assert len(cs) >= 1 and "Queimadura" in cs[0]["text"]

def test_termination():
    text = "a" * 10000
    cs = chunk_text(text, "doc.txt")
    assert len(cs) > 1

def test_empty():
    assert chunk_text("", "doc.txt") == []
    assert chunk_text("   ", "doc.txt") == []