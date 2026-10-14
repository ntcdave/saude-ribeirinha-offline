"""Monta o prompt para o Gemma 4 com contexto do RAG + citações obrigatórias.

Contrato de UI (cartão padrão — ver frontend/app.js renderGuideCard):
  TITULO: <tema curto, ex: Primeiros Socorros: Queimadura>
  PASSO 1..PASSO 6: <destaque curto> | <complemento simples>
  FONTE: <nome do arquivo>
Todo /api/ask retorna `card` nesse formato para o frontend renderizar igual.
"""
import re
import unicodedata

from .config import AVISO_SAUDE, SOURCE_TITLES

REFUSAL_MARKER = "nao encontrei isso nos documentos"

def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").lower()) if not unicodedata.combining(c))

def is_refusal(text: str) -> bool:
    return REFUSAL_MARKER in _fold(text)


SYSTEM = """Você é um assistente de saúde básica em português simples, para comunidades ribeirinhas e indígenas da Amazônia, funcionando OFFLINE.

Regras duras:
1. Responda APENAS com base nos TRECHOS abaixo. Se não estiver nos trechos, diga: "Não encontrei isso nos documentos oficiais que tenho aqui. Procure um agente de saúde/UBS."
2. Sempre cite a fonte no formato [Fonte: nome-do-arquivo].
3. Linguagem simples, frases curtas. Inclua quando procurar ajuda presencial.
4. Nunca invente dose, diagnóstico ou receita. Primeiro socorro só se estiver no trecho.
5. Termine com o aviso fixo.

FORMATO OBRIGATÓRIO (sempre assim, sem markdown, sem emoji, sem texto extra fora do formato):
TITULO: <tema curto, ex: Primeiros Socorros: Queimadura>
PASSO 1: <destaque de até 6 palavras> | <complemento em 1 frase simples>
PASSO 2: <destaque de até 6 palavras> | <complemento em 1 frase simples>
PASSO 3: <destaque de até 6 palavras> | <complemento em 1 frase simples>
PASSO 4: <destaque de até 6 palavras> | <complemento em 1 frase simples>
PASSO 5: <destaque de até 6 palavras> | <complemento em 1 frase simples>
PASSO 6: <destaque de até 6 palavras> | <complemento em 1 frase simples>
FONTE: <nome exato de um arquivo dos TRECHOS>
Use "NÃO" em maiúsculas no destaque quando for proibição (ex: "Não passe" no passo 2 de queimadura).
Use quantos passos forem necessários, de 2 a 6. Nunca repita nem invente passo para completar. Cada proibição (o que NÃO fazer) deve ter seu próprio passo, começando com NÃO.
"""


def build_prompt(pergunta: str, trechos: list[dict]) -> str:
    ctx = "\n\n".join(f"--- {t['source']} ---\n{t['text']}" for t in trechos) or "(sem trechos)"
    return (
        f"{SYSTEM}\n\nTRECHOS:\n{ctx}\n\nPERGUNTA: {pergunta}\n\n"
        f"Responda no FORMATO OBRIGATÓRIO acima e termine com: {AVISO_SAUDE}"
    )


_ICONES = [
    (("queimadura", "queimou", "brasa", "fogo", "fogao"), "local_fire_department"),
    (("cobra", "picada", "peconhento", "mordida", "arraia"), "warning"),
    (("dengue", "febre", "aedes", "termometro"), "thermostat"),
    (("agua", "cloro", "potavel", "ferver", "hipoclorito"), "water_drop"),
    (("diarreia", "soro", "desidratacao", "vomito"), "medication_liquid"),
    (("corte", "ferimento", "sangramento", "pele"), "healing"),
]


def _icone_para(texto: str) -> str:
    t = (texto or "").lower()
    for chaves, icone in _ICONES:
        if any(k in t for k in chaves):
            return icone
    return "health_and_safety"


def _limpa_markdown(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s or "")
    s = re.sub(r"[*_#>`]", "", s)
    return re.sub(r"\s+", " ", s).strip(" -|:")


def parse_card(resposta: str, pergunta: str = "", fontes: list[dict] | None = None) -> dict:
    """Normaliza qualquer texto do modelo para o cartão padrão da UI.

    Sempre retorna {titulo, icone, passos[3x{destaque, texto, alerta}], fonte}.
    Nunca levanta exceção — em último caso fatia a resposta em frases.
    """
    txt = (resposta or "").strip()
    if is_refusal(txt):
        return {
            "tipo": "sem_resposta",
            "titulo": "Não encontrei nos documentos",
            "icone": "help",
            "mensagem": "Não encontrei isso nos documentos oficiais que tenho aqui. Procure um agente de saúde ou a UBS mais próxima.",
            "passos": [],
            "fonte": "",
            "aviso": AVISO_SAUDE,
        }
    titulo = ""
    passos: list[dict] = []
    fonte = ""

    m = re.search(r"(?im)^titulo\s*:[ \t]*(.+)$", txt)
    if m:
        titulo = _limpa_markdown(m.group(1))

    for n in range(1, 7):
        m = re.search(rf"(?im)^passo\s*{n}\s*:[ \t]*(.+)$", txt)
        if not m:
            continue
        bruto = _limpa_markdown(m.group(1))
        if "|" in bruto:
            dest, resto = [p.strip() for p in bruto.split("|", 1)]
        elif " - " in bruto:
            dest, resto = [p.strip() for p in bruto.split(" - ", 1)]
        else:
            # primeira oração curta vira destaque
            partes = re.split(r"(?<=[.!])\s+", bruto, maxsplit=1)
            dest = partes[0][:60]
            resto = partes[1] if len(partes) > 1 else ""
            if len(dest.split()) > 8 and "," in dest:
                dest, resto = [p.strip() for p in dest.split(",", 1) + [resto]][:2]
        alerta = bool(re.search(r"\bn[ãa]o\b", dest, re.I))
        passos.append({"destaque": dest.strip(), "texto": resto.strip(), "alerta": alerta})

    m = re.search(r"(?im)^fonte\s*:[ \t]*(.+)$", txt)
    if m:
        fonte = _limpa_markdown(m.group(1)).strip("[]")
    if not fonte:
        m = re.search(r"\[Fonte:\s*([^\]]+)\]", txt)
        if m:
            fonte = _limpa_markdown(m.group(1))
    # normaliza "Fonte: ..." e colchetes
    fonte = re.sub(r"^fonte\s*:\s*", "", fonte or "", flags=re.I).strip("[] ").strip()

    allowed_map: dict[str, str] = {}
    counts: dict[str, int] = {}
    for f in (fontes or []):
        s = str((f or {}).get("source", ""))
        if not s:
            continue
        counts[s] = counts.get(s, 0) + 1
        allowed_map[s.lower()] = s
        stem = s.rsplit(".", 1)[0].lower() if "." in s else s.lower()
        allowed_map[stem] = s

    fonte_corrigida = False
    if allowed_map:
        key = (fonte or "").lower()
        stem = key.rsplit(".", 1)[0] if "." in key else key
        if key in allowed_map:
            fonte = allowed_map[key]
        elif stem in allowed_map:
            fonte = allowed_map[stem]
        else:
            # fonte inválida: usa a mais comum (empate: primeira)
            fonte_corrigida = True
            best = None
            bestc = -1
            vistos = set()
            for f in (fontes or []):
                s = str((f or {}).get("source", ""))
                if not s or s in vistos:
                    continue
                vistos.add(s)
                c = counts.get(s, 0)
                if c > bestc:
                    bestc = c
                    best = s
            if best:
                fonte = best
    if not fonte and (fontes or []):
        fonte = str((fontes or [])[0].get("source", ""))
        fonte_corrigida = True

    if not titulo:
        # "O que fazer se queimar..." -> "Primeiros Socorros: Queimadura"
        baixo = f"{pergunta} {txt}".lower()
        tema = "Orientações de Saúde"
        if any(k in baixo for k in ("queim", "brasa", "fogao", "fogo")):
            tema = "Primeiros Socorros: Queimadura"
        elif any(k in baixo for k in ("cobra", "picada", "mordida")):
            tema = "Primeiros Socorros: Picada de Cobra"
        elif any(k in baixo for k in ("dengue", "febre")):
            tema = "Febre & Dengue"
        elif any(k in baixo for k in ("cloro", "potavel", "agua")):
            tema = "Água Potável"
        elif any(k in baixo for k in ("diarreia", "soro", "desidrat")):
            tema = "Diarreia & Soro"
        titulo = tema

    if not passos:
        # recuperação: fatia bullets/frases da resposta livre em passos para manter o cartão padrão
        livres = re.split(r"\n+|(?:(?<=[.!])\s+)", re.sub(r"^(titulo|passo\s*\d|fonte)\s*:.*$", "", txt, flags=re.M))
        livres = [_limpa_markdown(x).lstrip("-•123). ") for x in livres]
        livres = [x for x in livres if len(x) > 12][:6]
        for resto in livres:
            dest = resto[:48].rsplit(" ", 1)[0] if len(resto) > 48 else resto
            passos.append({"destaque": dest, "texto": resto[len(dest):].lstrip(",. -"), "alerta": bool(re.search(r"\bn[ãa]o\b", dest, re.I))})

    passos = passos[:6]

    final_fonte = fonte or "documentos locais"
    fonte_pagina = None
    for f in (fontes or []):
        if str((f or {}).get("source", "")) == final_fonte:
            fonte_pagina = (f or {}).get("page")
            break
    if fonte_pagina is None and (fontes or []):
        fonte_pagina = (fontes or [])[0].get("page")
    return {
        "tipo": "guia",
        "titulo": titulo,
        "icone": _icone_para(f"{titulo} {pergunta} {txt}"),
        "passos": passos,
        "fonte": final_fonte,
        "fonte_titulo": SOURCE_TITLES.get(final_fonte, final_fonte),
        "fonte_pagina": fonte_pagina,
        "fonte_corrigida": fonte_corrigida,
        "aviso": AVISO_SAUDE,
    }
