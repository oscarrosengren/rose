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

## Install

```sh
gh repo clone oscarrosengren/rose ~/.local/share/rose-app   # or git clone
~/.local/share/rose-app/install.sh      # links ~/.local/bin/rose, shell integration, `rose setup`

rose add claude personal --adopt ~/.claude   # reuse an existing login, or sign in fresh without --adopt
rose add claude work                         # sign-in: pick the COMPANY Claude account
rose add codex main --adopt ~/.codex         # Codex uses a device code automatically over SSH
rose status
```

## Updating

```sh
rose update            # pull, check the new version starts, switch; refuses a broken update
rose update --check    # list what's new
rose update --rollback # back to the version before the last update
rose update --policy auto|notify|off   # default notify: rose tells you when an update is available
```

The code (the git checkout) is separate from your data (`~/.local/share/rose`: accounts, chats, names,
order, usage). Updating never touches the data, so there's nothing to reinstall or reconfigure.

**While chats are running:**
- Open chats keep working.
- Status line and hook calls use the new version right away.
- A running rose session switches to the new code the next time it restarts the chat (`move` or failover),
  carrying over its account, chat name and failover state.
- rose checks for updates at most every 6 hours, in the background, when you start a chat.

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

## Inside a chat

- **You can see you're in rose.** The status line starts with `🌹 rose · personal · excel-calcs`, the
  terminal title says the same, and rose prints a line before the chat opens.
- **Type `move` to switch accounts.** `move` goes to the next account in your order. `move to work`,
  `move personal` or `move codex` go to that account. Same tool: the chat is moved and reopened with its
  full history. Other tool: a new chat opens with the conversation handed over.
  - **Claude:** a prompt hook catches the message, so it never reaches the model.
  - **Codex:** rose notices the message in the chat log and closes Codex within about a second. Codex
    may start a reply first.
  - **In a chat started without rose,** `move` explains the `rose move` command instead.

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

## Order, threshold and failover

```sh
rose order claude:personal codex:main claude:work   # one order across both tools
rose threshold 95                                    # skip Claude accounts at/above 95% (5h or week)
rose chat "fix the tests"                            # new chat on the first available account in the order
rose failover claude ask                             # ask (default) | auto | off, per tool
```

- **New chats:** `rose chat` starts on the first account in the order that is signed in, not limited
  and under the threshold. `rose claude` with no `-a` uses your default, but moves on in the order
  if that account is over the threshold. In `ask` mode it asks first. An explicit `-a` always wins.
- **Usage limit hit:** the chat continues on the next account in the order. If that account uses the
  same tool, the chat is moved and resumed with its full history. If it uses the other tool, a new chat
  starts in the same folder with the conversation so far handed over (newest messages kept, about
  40k characters). It is told to check the folder before repeating anything. A chat name moves with it.
- **Resuming** a chat whose account is over the threshold or limited works the same way.
- **ask:** after you leave the limited session, rose asks before continuing elsewhere.
  **auto:** rose closes the limited session itself and continues. **off:** nothing moves.
- **Over the threshold mid-chat:** the status line shows `⚠ personal 96% → exit; next: main`. rose doesn't
  close a running chat for this, because you might be typing. The hard limit still fails over right away.
- The limited account gets a cooldown until its reset time. Each account is tried once per chat.

## Usage

```sh
rose usage install     # once: record Claude plan usage via the status line (it looks the same)
rose usage             # every account, in your order, with bars
rose usage uninstall   # restore the original status line
```

```
Claude · personal      #1 in order
  5h    ██████░░░░░░░░░░░░░░░░░░   27%  resets 02:30
  week  ███████░░░░░░░░░░░░░░░░░   28%  resets Sun 01:00
        seen 1m ago
```

- **Claude:** Claude Code gives its status line the plan's 5-hour and weekly usage. rose records it
  per account and then runs your original status line command.
- **Codex:** read from the rate-limit snapshots Codex writes into its own session files.

Neither needs network calls or tokens. Values are as last seen, updated while chats run. Once a
window's reset time passes, it shows "reset". Bars turn yellow and then red as usage rises (red at the
Claude threshold). Only subscription logins report usage (API keys don't).

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
- **Usage is "last seen", not polled.** It's recorded while chats run, so idle accounts show their last value.
- **No switching mid-chat at the threshold.** codexx switches before a new message is sent. rose only warns in
  the status line, and applies the threshold when you start, resume or fail over.
- **Handoffs between tools are a summary, not a resume.** The new tool gets the conversation text, but not
  the other tool's internal state.
- **Claude may ask you to confirm** when a chat continues under a different account.
  That is Claude Code's own session-owner check, and rose leaves it in place.
- **Not included:** the Desktop app, the web dashboard and the self-updater.
