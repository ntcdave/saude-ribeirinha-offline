"""Detecção determinística de situações de emergência (red flags).

Sem dependência de rede/LLM: a mensagem de alerta aparece imediatamente
e de forma confiável mesmo com Ollama fora do ar.
DEVE ser revisada por profissional de saúde antes de uso real.
"""
import unicodedata


def fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", (s or "").lower()) if not unicodedata.combining(c)
    )


# Lista dobrada (sem acentos, minúsculas). Revisar com profissional de saúde.
RED_FLAGS = [
    "nao respira", "parou de respirar", "sem respirar", "desmaiou", "desmaio", "inconsciente",
    "nao acorda", "convulsao", "convulsionando", "engasgou", "engasgado", "afogou", "afogamento",
    "nao para de sangrar", "sangramento forte", "hemorragia", "dor no peito", "infarto",
    "cobra mordeu", "picada de cobra", "picou de cobra", "mordida de cobra", "intoxic", "veneno",
]


def detect_emergency(pergunta: str):
    t = fold(pergunta)
    for flag in RED_FLAGS:
        if flag in t:
            return flag
    return None