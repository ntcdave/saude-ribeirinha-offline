""" Atalho p/ build do indice. Uso: python scripts/build-index.py (da raiz OU de backend/) """
import sys
from pathlib import Path
CWD = Path.cwd()
if (CWD / "app" / "rag").exists():
    sys.path.insert(0, str(CWD))  # rodando de dentro de backend/
elif (CWD / "backend" / "app").exists():
    sys.path.insert(0, str(CWD / "backend"))  # rodando da raiz
else:
    sys.path.insert(0, str(CWD))
from app.rag.ingest import main
main()
