#!/bin/sh
# Install rose from this checkout. Re-running is safe. Accounts and settings live in
# ~/.local/share/rose and are never touched by installing or updating.
set -e
APP="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
ln -sf "$APP/rose" "$BIN/rose"
echo "linked $BIN/rose -> $APP/rose"

case "${SHELL:-}" in
  */zsh) RC="$HOME/.zshrc"; SH=zsh ;;
  *)     RC="$HOME/.bashrc"; SH=bash ;;
esac
if ! grep -q 'rose init' "$RC" 2>/dev/null; then
  printf '\n# rose: switch Claude Code / Codex accounts\nexport PATH="$HOME/.local/bin:$PATH"\neval "$(rose init %s)"\n' "$SH" >> "$RC"
  echo "added shell integration to $RC (open a new terminal or: source $RC)"
fi

if [ -d "$HOME/.claude" ]; then
  "$APP/rose" setup
fi
cat <<'MSG'

Next:
  rose add claude personal --adopt ~/.claude   # reuse your existing Claude login, or: rose add claude personal
  rose add claude work                         # sign in with the other Claude account
  rose add codex main --adopt ~/.codex         # or: rose add codex main
  rose order claude:personal codex:main claude:work
  rose status
Update later with: rose update
MSG
