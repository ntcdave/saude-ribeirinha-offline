"""Busca local híbrida: vetorial (cosseno/numpy) + léxica (stopwords + radical),
fundidas por Reciprocal Rank Fusion. A resposta final sempre vem do Gemma 4.
"""
import json
import re
import unicodedata
import requests
import numpy as np

from .config import INDEX_PATH, OLLAMA_URL, EMBED_MODEL, TOP_K

_WORD = re.compile(r"[a-z0-9]+")  # sem acento: _norm remove diacríticos antes

# stopwords pt-BR enxutas e SEM acento (tokens já vêm sem diacrítico).
# Sem elas, "o/que/se/na" dominam o ranking e afogam "queimar/brasa".
_STOP = frozenset("""
a ao aos aquela aquelas aquele aqueles aquilo as ate com como da das de do dos
e em entre era eram esse essa esses essas este esta estes estas foi foram
ha isso isto ja lhe lhes mais mas me mesmo meu meus minha minhas muito na nas
nem no nos nao nunca o os ou para por que se sem ser seu seus sua suas sobre
tao tambem temos tem uma um uns umas vai vao qual quais quando onde quem
alguem pessoa pessoas vitima vitimas coisa coisas algo vez vezes caso forma
local modo jeito pode podem deve devem ter fazer ser estar sao seria
""".split())


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _norm(tok: str) -> str:
    """Normaliza p/ comparação: minúscula, sem acento, sem plural simples."""
    tok = _strip_accents(tok.lower())
    if len(tok) > 5 and tok.endswith("es"):
        return tok[:-2]
    if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def _content_tokens(s: str) -> list[str]:
    return [_norm(t) for t in _WORD.findall(_strip_accents(s.lower())) if t not in _STOP]


# Sinônimos linguagem do povo -> vocabulário das cartilhas (formas normalizadas).
# Ex: ninguém fala "lesão térmica", fala "queimou na brasa do fogão".
_SYN: dict[str, list[str]] = {
    "queimar": ["queimadura"], "queimou": ["queimadura"], "queima": ["queimadura"],
    "brasa": ["queimadura"], "lenha": ["queimadura"], "fogao": ["queimadura"],
    "fogo": ["queimadura"], "quente": ["queimadura"], "fervendo": ["queimadura"],
    "escaldar": ["queimadura"],
    "cobra": ["picada", "peconhento"], "jararaca": ["picada", "cobra"],
    "cloro": ["agua", "potavel"], "hipoclorito": ["agua", "cloro"],
    "diarreia": ["soro", "reidratacao"], "desidratacao": ["soro", "reidratacao"],
    "soro": ["reidratacao", "diarreia"],
    "mordida": ["picada"], "mordeu": ["picada"],
    "febre": ["temperatura", "termometro"], "dengue": ["aedes", "mosquito"],
}

# Âncoras de tratamento (peso 0.5): puxam o passo a passo junto do tema.
# Ex: quem pergunta de queimadura precisa do chunk "água/pano/bolhas".
_ANCHOR: dict[str, list[str]] = {
    "queimadura": ["agua", "pano", "bolha"],
    "picada": ["agua", "sabao", "soro"],
    "cobra": ["agua", "sabao", "soro"],
    "diarreia": ["agua", "soro"],
    "cloro": ["agua", "ferver"],
    "potavel": ["agua", "ferver"],
    "dengue": ["agua", "parado"],
}


def _expand_syn(qt: list[str]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    seen = set()
    for t in qt:
        if t not in seen:
            out.append((t, 1.0))
            seen.add(t)
    for t in qt:
        for s in _SYN.get(t, ()):
            if s not in seen:
                out.append((s, 0.8))
                seen.add(s)
    for t in qt:
        for s in _ANCHOR.get(t, ()):
            if s not in seen:
                out.append((s, 0.5))
                seen.add(s)
    # âncoras também valem p/ sinônimos já expandidos (ex: queimadura vinda de queimar)
    for t, _ in list(out):
        for s in _ANCHOR.get(t, ()):
            if s not in seen:
                out.append((s, 0.5))
                seen.add(s)
    return out


def _prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _lexical_ranking(pergunta: str, chunks: list[dict]) -> list[int]:
    """Ranking léxico TF-IDF: exata=peso cheio, mesmo radical (prefixo>=5)=0.7x.
    Ex: queimar~queimadura. Com IDF, 'fazer' (df=55) pesa pouco e 'queimar'
    (df=2) decide — sem isso só stopwords casavam."""
    import math
    from collections import Counter

    qt = _expand_syn(_content_tokens(pergunta))
    if not qt:
        qt = [(_norm(t), 1.0) for t in _tokens(pergunta)]
    toks, prefs = _chunk_cache(chunks)
    n = len(chunks)
    df = Counter()
    for s in toks:
        df.update(s)
    idf = {t: math.log((n + 1) / (1 + f)) for t, f in df.items()}
    scored = []
    for i, c in enumerate(chunks):
        s = 0.0
        for q, boost in qt:
            w = idf.get(q, math.log(n + 1)) * boost  # termo raro/ausente = peso alto
            if q in toks[i]:
                s += w
            elif len(q) >= 5 and q[:5] in prefs[i]:
                s += 0.7 * w
        scored.append((s, i))
    scored.sort(key=lambda x: -x[0])
    return [i for _, i in scored]


_CACHE: dict = {"n": -1, "toks": [], "prefs": []}

_IDX = {"mtime": None, "chunks": [], "mat": None}


def _chunk_cache(chunks: list[dict]):
    """Cache de tokens normalizados + prefixos por chunk (rebuild se mudar)."""
    if _CACHE["n"] != len(chunks):
        toks, prefs = [], []
        for c in chunks:
            s = set(_content_tokens(c["text"]))
            toks.append(s)
            prefs.append({t[:5] for t in s if len(t) >= 5})
        _CACHE.update({"n": len(chunks), "toks": toks, "prefs": prefs})
    return _CACHE["toks"], _CACHE["prefs"]


def _load():
    if not INDEX_PATH.exists():
        return [], None
    m = INDEX_PATH.stat().st_mtime
    if _IDX["mtime"] != m:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            chunks = data
        elif isinstance(data, dict):
            if "chunks" in data:
                chunks = data["chunks"]
            else:
                # version without chunks key: maybe chunks under other key
                chunks = data.get("chunks", [])
        else:
            chunks = []
        mat = None
        if chunks and (chunks[0].get("embedding") if isinstance(chunks[0], dict) else None):
            mat = np.array([c["embedding"] for c in chunks], dtype=np.float32)
        _IDX.update(mtime=m, chunks=chunks, mat=mat)
        _CACHE["n"] = -1
    return _IDX["chunks"], _IDX["mat"]


def _embed_query(q: str):
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": q}, timeout=30
        )
        r.raise_for_status()
        data = r.json()
        v = np.array(data.get("embeddings", [data.get("embedding")])[0], dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)
    except Exception:
        return None


def retrieve(pergunta: str, k: int = TOP_K) -> list[dict]:
    chunks, mat = _load()
    if not chunks:
        return []
    rankings: list[list[int]] = []
    # 1) vetorial (quando há embeddings + Ollama de pé)
    if mat is not None:
        q = _embed_query(pergunta)
        if q is not None:
            scores = mat @ q
            rankings.append(list(np.argsort(-scores)))
    # 2) léxica com stopwords + radical (sempre roda; compõe o híbrido com a vetorial)
    rankings.append(_lexical_ranking(pergunta, chunks))
    # 3) fusão RRF com peso léxico maior: neste corpus pequeno e com
    # perguntas coloquiais ("queimou na brasa"), o TF-IDF com sinônimos é
    # mais discriminativo que o cosseno (scores vetoriais ficam ~0.65-0.70
    # p/ tudo).
    fused = np.zeros(len(chunks))
    weights = [0.3] * (len(rankings) - 1) + [1.0] if rankings else []
    for rank, w in zip(rankings, weights):
        for r, i in enumerate(rank):
            fused[int(i)] += w / (60.0 + r)
    top = [int(i) for i in np.argsort(-fused)[:k]]
    # Expande com vizinhos da mesma fonte: o passo a passo costuma estar
    # no chunk ao lado (ex: o "FAÇA" no 102 e o "NÃO FAÇA" no 103). Cap 7.
    out, seen = [], set()
    for i in top:
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(chunks) and chunks[j]["source"] == chunks[i]["source"] and j not in seen:
                out.append(chunks[j])
                seen.add(j)
                if len(out) >= min(k + 4, 7):
                    return out
    return out
