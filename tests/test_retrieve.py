import app.rag.retrieve as R

def test_lexical_burn(small_index):
    chunks = R.retrieve("queimou na brasa do fogão", k=3)
    assert chunks
    assert any("queimadura" in (c["text"].lower()) or "brasa" in (c["text"].lower()) for c in chunks)

def test_synonym():
    # just ensure no crash
    R.retrieve("cobra mordeu", k=2)

def test_cap(small_index):
    chunks = R.retrieve("queimou", k=3)
    assert len(chunks) <= 7