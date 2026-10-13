#!/usr/bin/env bash
# Roda backend + index no Linux. Uso: bash scripts/run-dev.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv nao encontrado. Instale: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
[ -d .venv ] || uv venv
# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -r requirements.txt
python ../scripts/build-index.py

# IP da rede local p/ abrir no celular (mesmo Wi-Fi). Ignora docker/vbox (192.168.56.*).
CANDS=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)' | grep -v '^192\.168\.56\.' || true)
IP=$(echo "$CANDS" | grep -m1 '^192\.168\.1\.' || true)
[ -z "$IP" ] && IP=$(echo "$CANDS" | grep -m1 '^192\.168\.0\.' || true)
[ -z "$IP" ] && IP=$(echo "$CANDS" | head -n1 || true)
IP=${IP:-localhost}

echo ""
echo "=== Saude Ribeirinha Offline ==="
echo "PC:      http://localhost:8000"
echo "Celular: http://${IP}:8000  (mesmo Wi-Fi)"
echo "Se o celular nao abrir, libere o firewall (ufw allow 8000/tcp)"
echo ""
# 0.0.0.0 = acessivel pelo celular na mesma rede
# --reload-dir app: observa so o codigo, ignora .venv (evita loop de restart)
python -m uvicorn app.main:app --reload --reload-dir app --port 8000 --host 0.0.0.0
