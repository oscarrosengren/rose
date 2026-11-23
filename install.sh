#!/bin/sh
# rose installer.
#
#   curl -fsSL https://raw.githubusercontent.com/oscarrosengren/rose/main/install.sh | sh
#
# Safe to run again: it updates the existing copy. Your accounts, chats and settings live in
# ~/.local/share/rose and are never touched by installing or updating.
set -e

REPO="${ROSE_REPO:-https://github.com/oscarrosengren/rose.git}"
APP="${ROSE_APP:-$HOME/.local/share/rose-app}"
BIN="$HOME/.local/bin"

say() { printf '%s\n' "$*"; }
how_to_get() {
  case "$(uname -s)" in
    Darwin) say "  On a Mac, open Terminal and run:  xcode-select --install"
            say "  (that installs both git and Python), then run this installer again." ;;
    *)      say "  Ubuntu/Debian:  sudo apt install git python3"
            say "  Fedora:         sudo dnf install git python3"
            say "  Then run this installer again." ;;
  esac
}

# 1. What rose needs
if ! command -v git >/dev/null 2>&1; then
  say "rose needs git, which is not installed yet."; how_to_get; exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  say "rose needs Python 3, which is not installed yet."; how_to_get; exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  say "rose needs Python 3.9 or newer; this computer has $(python3 --version 2>&1)."; how_to_get; exit 1
fi
if ! command -v claude >/dev/null 2>&1 && ! command -v codex >/dev/null 2>&1; then
  say "Note: neither Claude Code (claude) nor Codex (codex) is installed yet. rose works with them;"
  say "install at least one before adding accounts."
fi

# 2. Get rose: the checkout this script lives in, or a copy from GitHub
SRC=""
case "$0" in
  */install.sh) d=$(cd "$(dirname "$0")" && pwd); [ -f "$d/rose" ] && SRC="$d" ;;
esac
if [ -z "$SRC" ]; then
  if [ -d "$APP/.git" ]; then
    say "Updating rose in $APP"
    git -C "$APP" pull -q --ff-only || say "(could not update the existing copy; keeping it as it is)"
  else
    say "Downloading rose to $APP"
    mkdir -p "$(dirname "$APP")"
    if ! git clone -q "$REPO" "$APP"; then
      say "Could not download rose from GitHub. Check the internet connection and try again."; exit 1
    fi
  fi
  SRC="$APP"
fi

# 3. Make the `rose` command available
mkdir -p "$BIN"
chmod +x "$SRC/rose" 2>/dev/null || true
ln -sf "$SRC/rose" "$BIN/rose"
rose_run() { python3 "$SRC/rose" "$@"; }
case "${SHELL:-}" in
  */zsh) RC="$HOME/.zshrc"; SH=zsh ;;
  *)     RC="$HOME/.bashrc"; SH=bash ;;
esac
if ! grep -q 'rose init' "$RC" 2>/dev/null; then
  printf '\n# rose: switch Claude Code / Codex accounts\nexport PATH="$HOME/.local/bin:$PATH"\neval "$(rose init %s)"\n' "$SH" >> "$RC"
fi

# 4. Updates install by themselves (unless you already chose otherwise), and Claude Code integration
rose_run update --policy auto --if-unset >/dev/null
if [ -d "$HOME/.claude" ]; then
  rose_run setup >/dev/null
fi

VERSION=$(rose_run --version)
say ""
say "Installed $VERSION. Updates install automatically."
say ""
say "Open a new terminal window, then add your accounts, for example:"
say "  rose add claude personal      (sign in with your personal Claude account)"
say "  rose add claude work          (sign in with your work Claude account)"
say "  rose add codex main           (sign in with your ChatGPT account)"
say "Then start with:  rose"
