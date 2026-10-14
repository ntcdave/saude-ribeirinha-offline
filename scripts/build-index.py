""" Atalho p/ build do indice. Uso: python scripts/build-index.py (da raiz OU de backend/) """
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rag.ingest import main

ap = argparse.ArgumentParser()
ap.add_argument("--force", action="store_true")
args = ap.parse_args()
main(force=args.force)