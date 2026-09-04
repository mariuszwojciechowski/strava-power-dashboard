#!/usr/bin/env bash
# Jednorazowy bootstrap maszyny (Debian) pod Strava Power Dashboard.
# Uruchom na VM jako użytkownik z sudo:
#   curl -fsSL https://raw.githubusercontent.com/mariuszwojciechowski/strava-power-dashboard/main/deploy/setup-vm.sh | sudo bash
# albo po sklonowaniu repo: sudo bash deploy/setup-vm.sh
set -euo pipefail

REPO_URL="https://github.com/mariuszwojciechowski/strava-power-dashboard.git"
APP_DIR="/opt/strava-power-dashboard"
APP_USER="stravadash"

need_sudo() { [ "$(id -u)" -eq 0 ] || exec sudo -E bash "$0" "$@"; }
need_sudo "$@"

echo "== pakiety systemowe =="
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-dev build-essential

echo "== użytkownik $APP_USER =="
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$APP_USER"

echo "== kod =="
if [ -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

echo "== venv + zależności =="
sudo -u "$APP_USER" bash -c "cd '$APP_DIR' && python3 -m venv venv && venv/bin/pip install -q --upgrade pip && venv/bin/pip install -q -r requirements.txt"

echo "== plik .env =="
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$APP_DIR/.env.example" "$ENV_FILE"
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "   utworzono $ENV_FILE z .env.example — WYPEŁNIJ STRAVA_CLIENT_ID/SECRET"
else
  echo "   $ENV_FILE już istnieje — nie ruszam"
fi

echo "== usługa systemd =="
cp "$APP_DIR/deploy/strava-dashboard.service" /etc/systemd/system/strava-dashboard.service
systemctl daemon-reload
systemctl enable --now strava-dashboard

echo "== pozwolenie na restart usługi z CI (bez pełnego sudo) =="
cat > /etc/sudoers.d/strava-dashboard-deploy <<EOF
$APP_USER ALL=(root) NOPASSWD: /bin/systemctl restart strava-dashboard, /bin/systemctl status strava-dashboard
EOF
chmod 440 /etc/sudoers.d/strava-dashboard-deploy

echo
echo "GOTOWE. Pozostało ręcznie:"
echo "  1. Uzupełnij $ENV_FILE (STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, BIKE_*_GEAR_ID/NAME)"
echo "     i skopiuj tokens.json (jeśli masz już autoryzację) do $APP_DIR/tokens.json"
echo "  2. Dodaj klucz publiczny deployu do /home/$APP_USER/.ssh/authorized_keys"
echo "  3. Dopisz do Caddyfile:"
echo "       strava.krasnal.cc { reverse_proxy 127.0.0.1:8322 }"
echo "     i: sudo systemctl reload caddy"
echo "  4. W ustawieniach appki Strava (developers.strava.com) ustaw"
echo "     Authorization Callback Domain: strava.krasnal.cc"
echo
systemctl --no-pager status strava-dashboard | head -5
