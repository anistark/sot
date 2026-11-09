#!/usr/bin/env python3
"""Write the data the docs site reads from sot itself.

The docs show each command's real ``--help`` output, the key bindings from
``sot --keys`` and the config template from ``sot --config-path``. This script
collects them into ``docs/src/_data/sot.json`` so the site never drifts from
the code. Run it before building the docs (``just docs-build`` does).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# A classic 80-column terminal and no colour, so the help text is the same on every machine.
os.environ["COLUMNS"] = "80"
os.environ["NO_COLOR"] = "1"
os.environ["PYTHON_COLORS"] = "0"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "src" / "_data" / "sot.json"

sys.path.insert(0, str(ROOT / "src"))

from sot.__about__ import __version__  # noqa: E402
from sot._app import build_parser  # noqa: E402
from sot._config import EXAMPLE  # noqa: E402
from sot._theme import CLASSIC_LOGO, CYBER_LOGO, THEMES  # noqa: E402
from sot.tui.keymap import all_bindings  # noqa: E402


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("sot's parser has no subcommands")


def _wrapping(formatter_class: type) -> type:
    """sot's formatters keep each help string on one line; wrap it for the docs, with argparse's hanging indent."""

    class Wrapping(formatter_class):  # type: ignore[valid-type, misc]
        def _split_lines(self, text: str, width: int) -> list[str]:
            return argparse.HelpFormatter._split_lines(self, text, width)

    return Wrapping


def _options(parser: argparse.ArgumentParser) -> list[dict]:
    options = []
    for action in parser._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        if action.help == argparse.SUPPRESS:
            continue
        options.append(
            {
                "flags": action.option_strings,
                "metavar": action.metavar,
                "choices": list(action.choices) if action.choices else None,
                "help": action.help,
            }
        )
    return options


def build() -> dict:
    parser = build_parser()
    subparsers = _subparsers(parser)
    for p in (parser, *subparsers.choices.values()):
        p.formatter_class = _wrapping(p.formatter_class)
    summaries = {a.dest: a.help for a in subparsers._choices_actions}

    commands = {
        "sot": {
            "usage": parser.format_usage().strip(),
            "help": parser.format_help().rstrip(),
            "summary": parser.description,
            "options": _options(parser),
        }
    }
    for name, sub in subparsers.choices.items():
        commands[name] = {
            "usage": sub.format_usage().strip(),
            "help": sub.format_help().rstrip(),
            "summary": summaries.get(name),
            "options": _options(sub),
        }

    keys = [
        {"id": binding_id, "key": binding.key, "description": binding.description}
        for binding_id, binding in all_bindings().items()
    ]

    return {
        "version": __version__,
        "commands": commands,
        "keys": keys,
        "config_example": EXAMPLE.rstrip(),
        "themes": list(THEMES),
        "logos": {"classic": list(CLASSIC_LOGO), "cyberpunk": list(CYBER_LOGO)},
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
