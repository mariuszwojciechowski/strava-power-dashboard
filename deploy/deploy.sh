#!/usr/bin/env bash
# Wdrożenie nowej wersji na VM. Uruchamiane przez GitHub Actions po SSH
# (jako użytkownik stravadash) albo ręcznie na maszynie.
set -euo pipefail

APP_DIR="/opt/strava-power-dashboard"
cd "$APP_DIR"

echo "== pobieram kod =="
git fetch --quiet origin main
git reset --hard --quiet origin/main    # .env/tokens.json/strava_data.db są gitignored, reset ich nie rusza
git log -1 --format='   %h %s'

echo "== zależności =="
venv/bin/pip install -q -r requirements.txt

echo "== restart usługi =="
sudo /bin/systemctl restart strava-dashboard

echo "== health check =="
for i in $(seq 1 20); do
  if curl -fsS -o /dev/null http://127.0.0.1:8322/; then
    echo "   OK — aplikacja odpowiada"
    exit 0
  fi
  sleep 1
done

echo "BŁĄD: aplikacja nie odpowiedziała w 20 s" >&2
sudo /bin/systemctl status strava-dashboard --no-pager | tail -20 >&2
exit 1
