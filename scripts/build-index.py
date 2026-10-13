""" Atalho p/ build do indice a partir da raiz. Uso: python scripts/build-index.py """
import sys
from pathlib import Path
CWD = Path.cwd()
CAND = CWD / "backend"
if CAND.exists():
    sys.path.insert(0, str(CAND))
else:
    sys.path.insert(0, str(CWD))
from app.rag.ingest import main
main()
