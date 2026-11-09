---
title: sot update
description: Move to a newer release. `sot update` stays on your major version; `sot upgrade` takes major versions too.
cmds: [update, upgrade]
---

## Which one

```sh
sot update              # newest minor or patch release of this major version
sot upgrade             # newest release, major versions included
sot update --dry-run    # show how sot is installed and what would run
```

Both work out how sot was installed (uv, pipx, Homebrew, ...) and go through that tool, so the install stays managed by it. `--dry-run` shows how sot is installed and what would run, without changing it.

## Windows

On Windows they print the command to run instead, since a running program can't replace itself.

Major releases can change key bindings or flags; read the [changelog](/changelog/) before `sot upgrade`.
