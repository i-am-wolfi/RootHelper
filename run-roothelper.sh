#!/bin/bash
# run-roothelper.sh — start|stop|restart|status|logs do RootHelper
# Mata a árvore inteira (sem patifaria de processo zumbi).

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$DIR/roothelper.pid"
LOGFILE="$DIR/roothelper.log"
PAT='RootHelper/.ven[v]'

die() { echo "❌ $*" >&2; exit 1; }
ok()  { echo "✅ $*"; }

is_running() {
  [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

sweep() {
  # varre restos pelo padrão (bracket evita self-match do pkill -f)
  pkill -9 -f "$PAT" 2>/dev/null
  sleep 1
}

cmd_start() {
  [[ -f "$DIR/bot.env" ]] || die "bot.env não encontrado (copie de bot.env.sample)"
  if is_running; then ok "já rodando (PID $(cat "$PIDFILE"))"; return 0; fi
  sweep
  cd "$DIR" || die "sem acesso a $DIR"
  [[ -x .venv/bin/python ]] || die "sem venv (rode: python -m venv .venv && .venv/bin/pip install -r requirements.txt)"
  echo "🚀 Iniciando RootHelper ..."
  set -a; . ./bot.env; set +a
  PYTHONPATH="$DIR/tools:${PYTHONPATH:-}" nohup .venv/bin/python bot.py >>"$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 10
  if is_running; then
    ok "rodando (PID $(cat "$PIDFILE"))"
  else
    rm -f "$PIDFILE"; echo "❌ falhou. Últimas linhas:" >&2; tail -15 "$LOGFILE" >&2; exit 1
  fi
}

cmd_stop() {
  if ! is_running; then rm -f "$PIDFILE"; sweep; echo "já estava parado."; return 0; fi
  echo "🛑 Parando (PID $(cat "$PIDFILE")) ..."
  kill -TERM "$(cat "$PIDFILE")" 2>/dev/null
  for _ in $(seq 1 15); do is_running || break; sleep 1; done
  sweep
  rm -f "$PIDFILE"
  ok "parado."
}

cmd_restart() { cmd_stop; sleep 2; cmd_start; }
cmd_status() {
  if is_running; then ok "RODANDO (PID $(cat "$PIDFILE"))"
  else echo "⏸️  PARADO."; fi
}
cmd_logs() { tail -n "${1:-50}" -f "$LOGFILE" 2>/dev/null || die "sem log ainda"; }

case "${1:-status}" in
  start) cmd_start;; stop) cmd_stop;; restart) cmd_restart;;
  status) cmd_status;; logs) cmd_logs "${2:-50}";;
  *) die "uso: $0 {start|stop|restart|status|logs}" ;;
esac
