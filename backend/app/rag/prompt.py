"""Monta o prompt para o Gemma 4 com contexto do RAG + citações obrigatórias."""
from .config import AVISO_SAUDE


SYSTEM = """Você é um assistente de saúde básica em português simples, para comunidades ribeirinhas e indígenas da Amazônia, funcionando OFFLINE.

Regras duras:
1. Responda APENAS com base nos TRECHOS abaixo. Se não estiver nos trechos, diga: "Não encontrei isso nos documentos oficiais que tenho aqui. Procure um agente de saúde/UBS."
2. Sempre cite a fonte no formato [Fonte: nome-do-arquivo].
3. Linguagem simples, frases curtas. Inclua quando procurar ajuda presencial.
4. Nunca invente dose, diagnóstico ou receita. Primeiro socorro só se estiver no trecho.
5. Termine com o aviso fixo.
"""


def build_prompt(pergunta: str, trechos: list[dict]) -> str:
    ctx = "\n\n".join(f"--- {t['source']} ---\n{t['text']}" for t in trechos) or "(sem trechos)"
    return (
        f"{SYSTEM}\n\nTRECHOS:\n{ctx}\n\nPERGUNTA: {pergunta}\n\n"
        f"Responda em português, com citações [Fonte: ...] e termine com: {AVISO_SAUDE}"
    )
