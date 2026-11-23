# rose: one launcher for all your Claude Code and Codex accounts

Built on the ideas in [codexx](https://github.com/JoRo-Code/codexx) (MIT), for both tools:

- **Separate accounts.** Each account has its own home (`CLAUDE_CONFIG_DIR` / `CODEX_HOME` under
  `~/.local/share/rose/accounts/<tool>/<name>`). Logins, history and sessions never mix.
- **Shared config.** Settings, `CLAUDE.md`/`AGENTS.md`, skills, agents, plugins and `config.toml` are
  symlinked from `~/.claude` and `~/.codex`, so you edit them once. Credentials are never shared.
- **Manual choice.** You choose with `-a`, `rose use`, a `.rose` pin, a default, or a picker.
- **Failover** when an account hits its usage limit: `off`, `ask` or `auto`, set per tool.
- **Chats move between accounts** (`rose move`, `rose resume --to`) with full history.

Python 3.9+, macOS/Linux, no dependencies. Tests: `python3 -I test_rose.py` (offline, uses fake CLIs).

## Setup

```sh
ln -s "$PWD/rose" ~/.local/bin/rose
echo 'eval "$(rose init bash)"' >> ~/.bashrc     # zsh: rose init zsh >> ~/.zshrc

rose add claude work         # browser sign-in: pick the COMPANY Claude account
rose add claude personal     # browser sign-in: pick your PERSONAL Claude account
rose add codex main          # browser sign-in: your ChatGPT/Codex account
#   or keep the existing ~/.codex login: rose add codex main --adopt ~/.codex
rose status
```

## Daily use

```sh
rose                          # menu: new chat, resume, move, status, failover
rose claude                   # Claude in this directory (account picked as below)
rose claude -a personal       # explicit account
rose codex  "fix the tests"   # native args/prompts pass through
rose sessions                 # chats from ALL accounts (this dir first; --all for everything)
rose resume                   # picker across all accounts and both tools
rose resume 1a2b --to personal   # move a chat, then resume it there
rose move 1a2b --to work

rose use work                 # this shell: plain `claude` now uses work
rose use codex main ; rose off
rose pin claude work          # this repo (and below) always uses work; switches on cd
rose default claude personal  # used when nothing else decides
```

## Naming chats

```sh
rose claude --name excel-calcs      # name a new chat up front (-n works too)
rose name 1a2b excel-calcs          # name an existing chat (or `rose name` for a picker)
rose name excel-calcs excel-v2      # rename;  rose name excel-v2 --clear  removes it
rose resume excel-calcs             # works across accounts and both tools; --to also works
```

Names are case-insensitive and unique (letters, digits, `.`, `-`, `_`). They stay with the chat when it
moves to another account. `rose resume` also accepts a title you set inside Claude with `/rename`, and
id prefixes still work.

**Which account a launch uses**, first match wins: `-a NAME` → `rose use` in this shell → `.rose` pin
→ `rose default` → the only account → a picker.

## When an account hits its usage limit

```sh
rose failover claude ask      # default: ask before continuing on another account
rose failover claude auto     # move and continue without asking
rose failover codex off       # never move
rose order claude work personal   # preferred order when more than two
```

- **ask:** after you leave the limited session, rose shows the reset time and asks
  `Continue this chat on Claude · personal? [Y/n]`. If you answer yes, it copies the chat and resumes it there.
- **auto:** rose watches the transcript. When the limit error appears, it closes the session, copies the
  chat, and resumes it on the next account with a "continue where you stopped" prompt.
- The limited account gets a cooldown until its reset time (`rose status`). Each account is tried
  once per chat. If all of them are limited, rose stops and tells you how to resume later.
- Only real usage-limit errors trigger this, not other errors. Limits are detected from Claude's
  `usage_limit_reached` entry and Codex's usage-limit error event.

## Live Claude usage

```sh
rose usage install     # once: record plan usage via Claude Code's status line (your status line looks the same)
rose usage             # personal  5h 42% (resets 20:50) · week 63% (resets Mon 09:00) · seen 2m ago
rose status            # same, next to each account's login and chats
rose usage uninstall   # restore the original status line
```

Claude Code gives its status line command the plan's 5-hour and weekly usage (`rate_limits`). rose
records it per account and then runs your original status line command. It updates whenever a chat
on that account is open; otherwise you see the last value and how old it is. After a window's reset
time passes, it shows "reset". Failover skips accounts known to be at 100% and prefers the least-used one.
Only subscription logins report usage (API keys don't).

## Defaults and per-account environment

```sh
rose defaults claude --model opus --effort high   # added at launch unless you pass your own
rose defaults codex --yolo                         # --dangerously-bypass-approvals-and-sandbox
rose env claude work                               # path of work's env file (KEY=value)
```

Ambient `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` (and similar variables) are removed for rose-launched tools,
because they override logins. If an account really uses a key, or Bedrock or Vertex, put it in that
account's env file. `rose status` warns if `~/.claude/settings.json` sets a key for every account.

## Limits compared with codexx

- **No switching mid-turn.** codexx swaps a Codex backend underneath an open terminal. Claude Code has no
  such interface, so rose restarts the native TUI with `--resume` instead. The history is kept, but the
  screen is redrawn.
- **Usage is "last seen", not polled.** Claude usage is recorded while chats run (see above). Codex
  usage isn't shown; use `/status` inside Codex.
- **Claude may ask you to confirm** when a chat continues under a different account.
  That is Claude Code's own session-owner check, and rose leaves it in place.
- **Not included:** the Desktop app, the web dashboard and the self-updater.
