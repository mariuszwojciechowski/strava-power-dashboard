# Wdrożenie Strava Power Dashboard (GCP + GitHub Actions)

Docelowo: `strava.krasnal.cc` → Caddy (HTTPS) → gunicorn na `127.0.0.1:8322`.
Deploy uruchamia się automatycznie po pushu na `main`.

Ta appka jest prostsza niż `bilans-kcal`: dane (`strava_data.db`, `tokens.json`)
i sekrety (`.env`) leżą **w katalogu repo**, ale są w `.gitignore` — `git reset
--hard` przy deployu ich nie dotyka.

## Rozkład na maszynie

| Ścieżka | Co to |
|---|---|
| `/opt/strava-power-dashboard` | kod (klon repo) + dane (`.env`, `tokens.json`, `strava_data.db`), właściciel `stravadash` |
| `/etc/systemd/system/strava-dashboard.service` | usługa |

## 1. Bootstrap maszyny (raz)

Po SSH na VM:

```bash
curl -fsSL https://raw.githubusercontent.com/mariuszwojciechowski/strava-power-dashboard/main/deploy/setup-vm.sh | sudo bash
```

Skrypt: instaluje pakiety, zakłada użytkownika `stravadash`, klonuje repo, robi
venv, kopiuje `.env.example` → `.env`, wstawia usługę systemd i wąską regułę
sudo (CI może tylko zrestartować tę jedną usługę).

Potem ręcznie:

```bash
sudo -u stravadash nano /opt/strava-power-dashboard/.env   # STRAVA_CLIENT_ID/SECRET, BIKE_*_GEAR_ID/NAME
```

Jeśli masz już lokalnie `tokens.json` (autoryzacja Strava OAuth wykonana na
swoim komputerze), skopiuj go na VM — inaczej trzeba przejść flow `/oauth/authorize`
jeszcze raz na `strava.krasnal.cc` (co wymaga wcześniej ustawionego callback domain,
patrz punkt 4 niżej).

```bash
scp tokens.json stravadash@34.56.100.135:/opt/strava-power-dashboard/tokens.json
```

## 2. Klucz SSH dla GitHub Actions

**Na swoim komputerze** (nie na VM) wygeneruj parę tylko do deployu:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/strava-dashboard-deploy -N "" -C "github-actions-deploy"
```

Klucz **publiczny** na VM:

```bash
sudo mkdir -p /home/stravadash/.ssh
sudo tee -a /home/stravadash/.ssh/authorized_keys < ~/.ssh/strava-dashboard-deploy.pub
sudo chown -R stravadash:stravadash /home/stravadash/.ssh
sudo chmod 700 /home/stravadash/.ssh && sudo chmod 600 /home/stravadash/.ssh/authorized_keys
```

Klucz **prywatny** do GitHuba: *Settings → Secrets and variables → Actions → New secret*

| Secret | Wartość |
|---|---|
| `DEPLOY_HOST` | statyczne IP maszyny (to samo co dla bilans-kcal) |
| `DEPLOY_USER` | `stravadash` |
| `DEPLOY_SSH_KEY` | zawartość `~/.ssh/strava-dashboard-deploy` (cały plik) |

Jeśli w repo `bilans-kcal` masz już te sekrety pod tymi samymi nazwami w
**tym** repo (`strava-power-dashboard`) — sekrety GitHuba są per-repo, więc
trzeba je dodać tutaj od nowa, nawet jeśli `DEPLOY_HOST` to ta sama wartość.

## 3. Caddy

Dopisz nowy blok do istniejącego `/etc/caddy/Caddyfile` (obok `fit.krasnal.cc`):

```
strava.krasnal.cc {
	reverse_proxy 127.0.0.1:8322
}
```

```bash
caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

Wymaga rekordu DNS `strava` → `34.56.100.135` (już zrobione).

## 4. Strava OAuth — callback domain

W ustawieniach appki na developers.strava.com ustaw **Authorization Callback
Domain** na `strava.krasnal.cc` — inaczej `/oauth/callback` nie zadziała
z publicznej domeny.

## Codzienne użycie

- Deploy: `git push` na `main` (albo *Actions → Deploy na GCP → Run workflow*)
- Logi aplikacji: `sudo journalctl -u strava-dashboard -f`
- Restart ręczny: `sudo systemctl restart strava-dashboard`
- Backup danych: `sudo tar czf ~/strava-backup.tar.gz -C /opt/strava-power-dashboard .env tokens.json strava_data.db`

Appka nie ma własnego logowania — jest publiczna bez autoryzacji, świadomie
(tylko Twoje dane treningowe, brak wrażliwych danych innych osób).
