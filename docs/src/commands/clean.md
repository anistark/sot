---
title: sot clean
description: Finds caches, logs, temp files and leftovers on your machine, shows how much each one takes, and removes only what you tick.
cmds: [clean]
outlineDepth: 3
---

## Usage

```sh
sot clean                      # Clean view: tick rows, then clean
sot clean --dry-run            # print what would go, delete nothing
sot clean --force              # also remove data still in use (see below)
sot clean --privacy            # also clear browser cookies, history and site data
sot clean --projects ~/code    # also clear node_modules, target, .venv… in idle projects
sudo sot clean                 # include system logs and temp files that need root
sot clean -d                   # clean in the background, every hour (see below)
```

In the Clean view:

| Key | Action |
| --- | --- |
| `space` | Tick a row |
| `a` | Tick all |
| `d` | Dry run |
| `c` | Clean (asks first) |
| `f` | Toggle force |
| `p` | Toggle privacy |
| `r` | Rescan |

## What it finds

- **Browsers**: caches of Chrome, Chromium, Edge, Brave, Vivaldi, Opera, Arc, Firefox, LibreWolf, Zen and Safari, free space in their databases, and old session snapshots
- **Apps**: Electron app caches (Slack, Discord, VS Code, Cursor, Claude, Obsidian…)
- **Dev tools**: Homebrew, pip, npm, pnpm, Yarn, Bun, uv, Go, Cargo, Gradle, Android and Composer caches; Xcode DerivedData, simulator caches and old device support
- **Coding agents**: Claude Code, Codex, pi, opencode and Kilo Code caches, and old Claude Code and Cursor binaries
- **System**: app and system logs, old temp files, Trash, crash dumps, thumbnails, the macOS installer leftovers, the systemd journal and old snaps on Linux, downloaded updates and Prefetch on Windows
- **Review only**: models (Ollama, LM Studio, Hugging Face), VM disks (Docker, OrbStack, Colima), simulators, toolchains and backups are measured and shown, never deleted

## Safety

- Asks before deleting, in the view and in the printed flow
- Conversation history, sessions, credentials and config are never touched
- Temp folders and logs only lose files older than a few days; folders and sockets stay
- Fonts, Spotlight, iCloud state, virtualenvs and downloaded browsers inside cache folders are kept
- Symlinks are removed, never followed
- Root-only targets are skipped unless you run with `sudo`
- `--force` is needed for in-use data: the newest browser session (the one that restores your tabs), browser copies still open, the newest device support files and projects touched in the last 14 days

## On a schedule

`sot clean -d` cleans in the background: hourly, unless you pass `daily`, `weekly` or `monthly` or set `every` under `[clean]` in the [config](/configuration/). It registers a job with launchd on macOS and a systemd user timer on Linux, or cron where there's no user systemd, so nothing stays running between runs and the schedule survives a reboot. A run the machine slept through happens when it wakes, except under cron. Windows isn't supported yet.

```sh
sot clean -d daily                # start, or change the schedule
sot clean --scheduled --dry-run   # what a run would remove right now
sot clean -d status               # schedule, last run and log
sot clean -d stop                 # turn it off
```

Nobody is there to confirm a run, so it removes less than `sot clean`:

- It only clears entries nothing has touched for 3 days, so apps you're using and warm builds keep their caches. `--force` lifts this.
- It never touches the Trash, Mail attachments, the Go cache, anything that needs root, or other apps' sandboxes in `~/Library/Containers`, where macOS would stop it to ask you.

`--force`, `--privacy` and `--projects` given with `-d` apply to every run. macOS may ask once about a `--projects` folder in Documents or on an external drive, and the run waits for your answer. What each run removed goes in `~/.local/state/sot/clean.log`. A schedule changed in the config applies the next time you run `sot clean -d`. On Linux, a systemd timer only runs while you're logged in unless you run `loginctl enable-linger`.

## Details

### Browser sessions

Browsers keep many saved copies of your open tabs and only read the newest. `sot clean` removes the old ones. `--force` removes the newest too, so the browser starts with no tabs to restore. Quit the browser first, or it writes the session straight back.

| Browser | Old snapshots | Also with `--force` |
| --- | --- | --- |
| Chrome, Chromium, Edge, Brave, Vivaldi, Opera, Arc | All but the newest `Session_*`, `Tabs_*` and `Apps_*` in each profile's `Sessions` folder | The newest of each |
| Firefox, LibreWolf, Zen | `sessionstore-backups/upgrade.jsonlz4-*` | `sessionstore.jsonlz4` and the `recovery` and `previous` files |

### Privacy

`--privacy` adds per-browser rows for cookies, history and site data (IndexedDB, local storage, service workers), plus recent items and macOS window state over 30 days old. Clearing cookies signs you out of every site. Firefox keeps history and bookmarks in one database, so its history is left alone.

### Projects

`--projects DIR` looks for `node_modules`, `.next`, `target`, `.venv`, `__pycache__`, `Pods`, `.build`, Gradle `build` and more. A folder only counts when the file that rebuilds it sits beside it (`target` next to `Cargo.toml`, `node_modules` next to `package.json`).

### Coding agents

Only installed agents are listed, and only caches, logs and scratch folders are touched.

| Agent | Cleaned |
| --- | --- |
| Claude Code | `~/.claude/{cache,paste-cache,debug,shell-snapshots,session-env,statsig}`, `~/.cache/claude`, `~/Library/Caches/claude-cli-nodejs`, and binaries in `~/.local/share/claude/versions` other than the newest, the linked one and any running |
| Codex | `~/.codex/{.tmp,log}`, `~/.cache/codex-runtimes` |
| pi | `~/.pi/{cache,logs}`, `~/.cache/pi` |
| opencode | `~/.cache/opencode`, `~/.local/share/opencode/{cache,log}` |
| Kilo Code | `~/.kilocode/cache`, and `kilocode.kilo-code/{cache,checkpoints}` in VS Code, Cursor and VSCodium storage |

Left alone: `~/.claude/projects` (what `claude --resume` reads) and `~/.gemini/tmp`.

### Relocated directories

Paths follow these variables from the shell you run `sot` in: `CLAUDE_CONFIG_DIR`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `APPDATA`, `LOCALAPPDATA`, `VSCODE_PORTABLE`, `CARGO_HOME`, `RUSTUP_HOME`, `GOPATH`, `GOMODCACHE`, `GOCACHE`, `GRADLE_USER_HOME`, `NVM_DIR`, `UV_CACHE_DIR`, `BUN_INSTALL_CACHE_DIR`, `HF_HOME` and `OLLAMA_MODELS`. Run `sot clean --dry-run` to see the resolved paths.
