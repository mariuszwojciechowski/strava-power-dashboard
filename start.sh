#!/bin/bash
cd "$(dirname "$0")"

if [ -f app.pid ] && kill -0 "$(cat app.pid)" 2>/dev/null; then
  echo "Aplikacja już działa (PID $(cat app.pid)) - http://localhost:5050"
  exit 0
fi

source venv/bin/activate
nohup python app.py > app.log 2>&1 &
echo $! > app.pid
sleep 1
echo "Uruchomiono na http://localhost:5050 (PID $(cat app.pid))"
echo "Logi: tail -f $(pwd)/app.log"
echo "Zatrzymanie: ./stop.sh"
