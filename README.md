# rose: one launcher for all your Claude Code and Codex accounts

Use several Claude Code and Codex accounts on one computer, for example a personal Claude, a work
Claude and a ChatGPT account, and switch between them without logging out. Built on the ideas in
[codexx](https://github.com/JoRo-Code/codexx) (MIT), for both tools:

- **Separate accounts.** Each account has its own login, history and sessions. Settings, `CLAUDE.md` /
  `AGENTS.md`, skills, agents, plugins and `config.toml` are shared, so you set them up once.
  Credentials are never shared.
- **Choose the account yourself,** per chat, per terminal or per project folder, or let rose follow
  your order.
- **Type `move` in a chat** to continue it on another account.
- **Usage limits:** when an account runs out, the chat continues on the next one. rose can ask first,
  do it automatically, or do nothing.
- **Usage overview** with bars for every account.
- **Named chats** (`rose resume excel-calcs`) across all accounts and both tools.
- **Updates install by themselves,** without touching your accounts or settings.

macOS and Linux, Python 3.9+, no other dependencies.

## Install

Paste this into a terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/oscarrosengren/rose/main/install.sh | sh
```

What the installer does:
1. **Checks for git and Python 3.9+.** If one is missing, it says how to get it (on a Mac:
   `xcode-select --install`) and stops without changing anything.
2. **Downloads rose** to `~/.local/share/rose-app`. If it's already there, it updates it instead.
3. **Adds the `rose` command** (`~/.local/bin/rose`), plus one line in `~/.zshrc` or `~/.bashrc` so
   `rose use` and folder pins work.
4. **Turns on automatic updates,** unless you already chose a different update setting.
5. **Connects to Claude Code,** if `~/.claude` exists: it adds the 🌹 status line, usage recording and the
   `move` hook (see [Claude Code integration](#claude-code-integration)).

Running it again is always safe. Then **open a new terminal** and add your accounts:

```sh
rose add claude personal     # sign in with your personal Claude account
rose add claude work         # sign in with your work Claude account
rose add codex main          # sign in with your ChatGPT account
rose                         # menu: new chat, resume, move, status, ...
```

Already signed in to Claude Code or Codex? Keep that login and its history by adopting it instead of
signing in again: `rose add claude personal --adopt ~/.claude`, `rose add codex main --adopt ~/.codex`.
On a computer without a screen (over SSH), Codex sign-in uses a code you enter on another device.

**Moving from an older copy** (for example one run from a git folder you cloned yourself): run the
installer. It points the `rose` command, the status line and the hook at the new copy. Your
accounts and settings stay as they are.

### Where things live

| What | Where | Touched by updates? |
|---|---|---|
| rose itself (the code) | `~/.local/share/rose-app` | yes, replaced by new versions |
| The `rose` command | `~/.local/bin/rose`, a link to the code | no |
| Your accounts, chats, names, order, usage, settings | `~/.local/share/rose` | **never** |
| Shared Claude / Codex config | `~/.claude`, `~/.codex` | only by `rose setup` (status line + hook) |

### Uninstall

```sh
rose setup --remove                                   # give Claude Code its original status line back
rm ~/.local/bin/rose && rm -rf ~/.local/share/rose-app
# optional, deletes your rose accounts (logins and chat history): rm -rf ~/.local/share/rose
```

Then remove the `# rose` lines from `~/.zshrc` or `~/.bashrc`.

### Fixing a broken Codex install

Codex is sometimes installed as one bare `codex` file, without the helper programs that come with it.
That copy starts, but fails in ways that look like rose problems, even though plain `codex` fails the
same way:

- `Error: this CLI has no complete local package; install a packaged Codex CLI ... --no-daemon`
- Codex can't run any commands (and so can't install tools or reach Google Drive, Gmail, ...):
  "the command tool failed to start: its codex-code-mode-host executable is missing"

rose already starts Codex with `--no-daemon`, which avoids the first error but not the second. The fix
is to install Codex as the full package. With Node.js installed:

```sh
ls -l "$(command -v codex)"     # a large file, not a link into node_modules? then it's the bare copy
cp -p "$(command -v codex)" ~/codex-old.bak                  # keep a backup
rm "$(command -v codex)"                                     # npm won't replace a file it didn't install
npm install -g --prefix ~/.local @openai/codex               # installs to ~/.local/bin/codex
hash -r && codex --version
```

Your Codex logins, chats and settings in `~/.codex` (and rose's Codex accounts) are not touched. To
update Codex later, run the same `npm install` line again. Once the new version works, delete the
backup with `rm ~/codex-old.bak`.

## Updates

**Updates install by themselves.** When you start a chat, rose checks GitHub in the background (at most
every 6 hours, never slowing the start) and installs new versions:
- **Your data is never touched:** accounts, chats and settings live apart from the code.
- **Broken updates are refused:** if a new version doesn't start, rose keeps the one that works.
- **Open chats keep running,** and switch to the new version the next time they restart (`move` or failover).

```sh
rose update                    # update right now
rose update --check            # see what's new
rose update --rollback         # go back to the previous version (pauses automatic updates)
rose update --policy notify    # tell me instead of installing; or: auto (default), off
```

If something goes wrong, rose says so in plain words and keeps the version that works. For example:
"Couldn't reach GitHub (is the internet connected?). rose stays on version 0.3.0, which keeps working."
If rose's own files were edited on your computer, it won't overwrite them. `rose update --force` saves
those edits aside (with `git stash`) and updates.

## Daily use

```sh
rose                          # menu
rose claude                   # Claude in this folder (account picked as below)
rose claude -a personal       # a specific account
rose codex  "fix the tests"   # Codex; normal codex/claude options and prompts pass through
rose chat "fix the tests"     # first available account in your order, either tool
rose sessions                 # chats from ALL accounts (this folder first; --all for everything)
rose resume                   # pick any chat, from any account and either tool
rose resume excel-calcs       # by name; --to work moves it first
rose status                   # accounts, logins, usage, limits

rose use work                 # this terminal: plain `claude` now uses work
rose use codex main ; rose off
rose pin claude work          # this project folder (and below) always uses work
rose default claude personal  # used when nothing else decides
```

**Which account a new chat uses** (first match wins): `-a NAME` → `rose use` in this terminal →
`.rose` pin for the folder → `rose default` → the only account → a picker. If that account is over
your threshold, rose moves on in your order. An explicit `-a` always wins.

Everything else works as usual: rose starts the real `claude` / `codex`, so slash commands, models,
tools and permissions are unchanged. Their own subcommands (`rose claude mcp ...`,
`rose codex exec ...`) run under the chosen account.

## Inside a chat

- **You can see you're in rose.** In Claude Code the status line starts with
  `🌹 rose · personal · excel-calcs`. Codex has no place for custom text inside its chat screen, so there
  the 🌹 shows in the window or tab title (rose turns off Codex's own title so it doesn't overwrite it).
  rose also prints a line before the chat opens.
- **Type `move` to switch accounts.** `move` goes to the next account in your order. `move to work`,
  `move personal` or `move codex` go to that account. Same tool: the chat is moved and reopened with its
  full history. Other tool: a new chat opens with the conversation handed over.
  - **Claude:** a prompt hook catches the message, so it never reaches the model.
  - **Codex:** rose notices the message in the chat log and closes Codex within about a second. Codex
    may start a reply first.
  - **In a chat started without rose,** `move` explains the `rose move` command instead.
- **The in-app `/resume`** only lists the current account's chats. Use `rose resume` to see them all.

## Naming chats

```sh
rose claude --name excel-calcs      # name a new chat up front (-n works too)
rose name 1a2b excel-calcs          # name an existing chat (or `rose name` for a picker)
rose name excel-calcs excel-v2      # rename;  rose name excel-v2 --clear  removes it
rose resume excel-calcs             # works across accounts and both tools
```

Names are case-insensitive and unique (letters, digits, `.`, `-`, `_`), and stay with the chat when it
moves, including to the other tool. `rose resume` also accepts a title you set in Claude with `/rename`,
or the first characters of a chat id.

## Order, threshold and switching

```sh
rose order claude:personal codex:main claude:work   # your order, across both tools
rose order --from next        # on a switch, continue after the current account (default)
rose order --from top         # on a switch, always start again at #1
rose threshold 95             # skip Claude accounts at/above 95% (5-hour or weekly)
rose failover                 # show how every switch is handled
```

**When rose switches:** an account hits its usage limit, or you start or resume a chat on an account
that is over the threshold. If the next account uses the same tool, the chat is moved and resumed
with its full history. If it uses the other tool, a new chat starts in the same folder with the
conversation so far handed over (newest messages kept, about 40k characters). It is told to check the
folder before repeating anything. A chat name moves with the chat. A limited account is skipped until
its reset time, and each account is tried once per chat.

**Where it switches to.** With the order personal → Codex → work, if you're on Codex and it runs out:

| Setting | Goes to |
|---|---|
| `--from next` (default) | work, then personal (continues after Codex, wraps around) |
| `--from top` | personal, then work (back to #1 whenever it has quota) |

Accounts at or above the threshold come last either way.

### Ask, auto or off

Each switch is `ask` (rose asks you first), `auto` (rose switches by itself) or `off` (never).

```sh
# Simple: one setting per tool, for switches away from that tool
rose failover all ask                 # every switch
rose failover claude auto             # switches away from Claude accounts
rose failover codex ask

# Advanced: a setting per switch, between two accounts
rose failover personal codex auto     # personal → Codex: automatic
rose failover codex work ask          # Codex → work: ask first
rose failover personal work off       # never move a personal chat to work
rose failover personal work default   # remove that rule again
rose failover advanced off            # back to simple (rules are kept for later)
```

Setting a rule turns on advanced mode. Any switch without its own rule uses the simple setting for the
tool it switches away from. `rose failover` lists every switch and how it's handled:

```
  Mode:   advanced (per switch)
    Claude · personal  → Codex · main       auto
    Claude · personal  → Claude · work      off
    Codex · main       → Claude · work      ask   (default for Codex)
```

### What "ask" looks like

**A chat hits its limit.** The app shows its usual limit message. Leave it (`/exit`, or Ctrl-C twice)
and rose asks right there in the terminal:

```
rose: Claude · personal hit its five-hour limit (until 20:50).
Continue on which account?
   1) Codex · main       (new chat with this conversation handed over)
   2) Claude · work      (moves this chat)
  choose (enter = 1, n = stay here, keep the chat): 
rose: handing chat excel-calcs over from Claude · personal to Codex · main.
🌹 rose · Codex · main · excel-calcs · failover ask · type 'move' to switch account
```

With a single possible account it's a yes/no question instead:
`Continue on Codex · main (new chat with this conversation handed over)? [Y/n]`. Enter means yes. If
you answer `n`, the chat is saved and `rose resume excel-calcs` continues it later.

**Starting or resuming on an account over the threshold:**

```
personal is at 96% (threshold 95%). Start on Codex · main instead? [Y/n] n
```

With `auto` you see no question: rose closes the limited chat itself as soon as the limit appears,
and the next chat opens. Without a terminal (scripts), `ask` never switches.

**Over the threshold mid-chat:** the status line shows `⚠ personal 96% → type 'move' (main)`. rose
doesn't close a running chat for this, because you might be typing. The hard limit still switches
right away.

With `auto`, a chat can continue on an account you might want to keep separate, for example from
personal to work. Use `ask` or `off` for that switch in advanced mode.

## Usage

```sh
rose usage             # every account, in your order, with bars
rose dashboard         # the same, kept open and redrawn every 5 s (Ctrl-C to quit); -i 2 for every 2 s
rose usage bar on      # also show every account's usage in the Claude status line (off: rose usage bar off)
```

```
Claude · personal      #1 in order
  5h    ██████░░░░░░░░░░░░░░░░░░   27%  resets 02:30
  week  ███████░░░░░░░░░░░░░░░░░   28%  resets Sun 01:00
        seen 1m ago
```

- **Claude:** Claude Code gives its status line the plan's 5-hour and weekly usage. rose records it
  per account (that's part of `rose setup`, which the installer runs).
- **Codex:** read from the usage snapshots Codex writes into its own session files.

Neither needs network calls or tokens. Values are as last seen, updated while chats run. Once a
window's reset time passes, it shows "reset". Bars turn yellow and then red as usage rises (red at the
Claude threshold). Only subscription logins report usage (API keys don't).

**Dashboard:** `rose dashboard` (or `rose usage --watch`, or *Usage dashboard* in the `rose` menu)
keeps the usage screen open in a terminal and redraws it every few seconds. Leave it running in a
spare window or tmux pane. It shows new numbers as soon as any chat on any account reports them.

**In the status line:** with `rose usage bar on`, every Claude chat's status line shows each account's
usage next to the 🌹 marker:

```
🌹 rose · personal  │ personal ▃37% · main ▃27% · work ▁5%  │ home:misc_claude_sessions oscar
```

Each account shows the fuller of its 5-hour and weekly windows (the one that runs out first), with
the same green/yellow/red colors. `?` means no usage has been seen for that account yet.

## Claude Code integration

`rose setup` (run by the installer) changes one file, `~/.claude/settings.json`, and keeps a backup next
to it (`settings.json.bak-rose`):
- **Status line:** rose's status line adds the 🌹 marker and records usage, then runs your previous status
  line command, so it still shows what it did before.
- **`UserPromptSubmit` hook:** catches `move` in rose chats. Your other hooks are kept.

`rose setup --remove` restores your status line and removes the hook.

## Defaults and per-account environment

```sh
rose defaults claude --model opus --effort high   # added at launch unless you pass your own
rose defaults codex --yolo                         # --dangerously-bypass-approvals-and-sandbox
rose env claude work                               # path of work's env file (KEY=value)
```

`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and similar variables are removed for chats rose starts, because
they would override the account's login. If an account really uses a key, or Bedrock or Vertex, put it
in that account's env file. `rose status` warns if `~/.claude/settings.json` sets a key for every account.

## Developing rose

Keep your development folder separate from the copy you use every day:

```sh
git clone https://github.com/oscarrosengren/rose ~/dev/rose    # work here
python3 -I ~/dev/rose/test_rose.py                             # offline tests with fake claude/codex
python3 ~/dev/rose/rose status                                 # try a change without installing it
```

- **Your everyday `rose`** stays the installed copy in `~/.local/share/rose-app`. It never runs your
  unfinished work, and its updates aren't blocked by your uncommitted changes.
- **Pushing to `main` is a release.** Everyone with automatic updates, you included, gets each push
  to `main` within a few hours. Run the tests before pushing.
- **Both copies use the same data** in `~/.local/share/rose`, so be careful when testing against your
  real accounts. Set `ROSE_HOME=/tmp/rose-test` to use a throwaway data folder.
- **Changes reach the status line and hook** at their next call, and running chats pick them up at
  their next restart. Keep stored data (`~/.local/share/rose/*.json`) readable by older versions, or
  migrate it when loading.

## Limits compared with codexx

- **No switching mid-turn.** codexx swaps a Codex backend underneath an open terminal. Claude Code has no
  such interface, so rose restarts the app with `--resume` instead. The history is kept, but the screen
  is redrawn.
- **Usage is "last seen", not polled.** It's recorded while chats run, so idle accounts show their last value.
- **No switching mid-chat at the threshold.** codexx switches before a new message is sent. rose warns in
  the status line, and applies the threshold when you start, resume, move or fail over.
- **Handoffs between tools are a summary, not a resume.** The new tool gets the conversation text, but not
  the other tool's internal state.
- **Claude may ask you to confirm** when a chat continues under a different account.
  That is Claude Code's own session-owner check, and rose leaves it in place.
- **Updates follow `main` on GitHub.** There are no signed releases or checksums, so you trust the
  repository and HTTPS.
- **Not included:** codexx's Desktop app integration and web dashboard.
