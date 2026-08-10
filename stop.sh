#!/bin/bash
cd "$(dirname "$0")"

if [ -f app.pid ]; then
  PID="$(cat app.pid)"
  if kill "$PID" 2>/dev/null; then
    echo "Zatrzymano (PID $PID)"
  else
    echo "Proces $PID już nie działał"
  fi
  rm -f app.pid
else
  echo "Brak pliku app.pid - aplikacja nie jest uruchomiona przez start.sh"
fi
