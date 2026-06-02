# SOT Contributing Guidelines

The SOT community appreciates your contributions via [issues](https://github.com/anistark/sot/issues) and [pull requests](https://github.com/anistark/sot/pulls).

When submitting pull requests, please follow the style guidelines of the project, ensure that your code is tested and documented, and write good commit messages, e.g., following [these guidelines](https://chris.beams.io/posts/git-commit/).

By submitting a pull request, you are licensing your code under the project [license](LICENSE) and affirming that you either own copyright (automatic for most individuals) or are authorized to distribute under the project license (e.g., in case your employer retains copyright on your work).

## Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) - Fast Python package manager (recommended)
- [just](https://github.com/casey/just) - Command runner (recommended)

### Method 1: Using uv (Recommended)

```sh
# Sync dependencies including dev dependencies
uv sync --dev

# Install in development mode
uv pip install -e .

# Or use the justfile command
just setup-dev
```

### Method 2: Traditional pip setup

```sh
python3 -m venv .venv
source .venv/bin/activate

# Install Dependencies
pip install -e .

# Set Up Development Environment
just setup-dev
```

This will install additional development dependencies like `watchdog` and `textual-dev` for hot reloading and advanced debugging.

## 🔧 Development Workflow

### Installation Commands

Before running SOT, you may want to install it. Here are the available installation commands:

#### Build SOT Locally
```sh
just build
```
Builds SOT in the current virtual environment. Useful for testing the package locally without system-wide installation.

#### Install SOT System-wide
```sh
just install
```
Installs SOT system-wide using `uv pip install --system --break-system-packages .`. This makes the `sot` command available globally from any terminal.

#### Uninstall SOT
```sh
just uninstall
```
Uninstalls SOT from both system-wide and local installations, then cleans up all development files. Use this to completely remove SOT from your system.

### Running SOT

To install and run SOT directly:

```sh
just sot
```

This command will:
1. Install SOT in editable mode using `uv pip install .`
2. Run the SOT application with any provided arguments

Examples:
```sh
# Run SOT normally
just sot

# Show SOT help
just sot --help

# Run disk benchmarking
just sot bench

# Show benchmark help
just sot bench --help
```

### Hot Reload Development (Recommended)

For the best development experience with automatic restarts on file changes:

```sh
just dev-watch
```

### Alternative Development Modes

```sh
# Basic development mode
just dev

# Development with debug logging to file
just dev-debug

# Development with Textual console for advanced debugging
just dev-console
```

### Useful UV Commands

If you're using uv for package management, here are some helpful commands:

```sh
# Sync dependencies
uv sync

# Sync dev dependencies
uv sync --dev

# Add a new package
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Remove a package
uv remove package-name

# Show dependency tree
uv tree

# Generate lock file
uv lock
```

### Development Tools

#### VS Code Integration

If using VS Code, the project includes debug configurations in `.vscode/launch.json`:

- **SOT Development** - Basic development mode with debugging
- **SOT with Network Interface** - Test with specific network interface
- **SOT Production Mode** - Test the production build

#### Textual Console

For advanced debugging, run the Textual console in a separate terminal:

```sh
# Terminal 1
textual console

# Terminal 2
just dev-console
```

This provides real-time insights into widget rendering, events, and performance.

#### Screenshots and Debugging

While in development mode, you can:
- Press `s` to save a screenshot
- Press `d` to toggle dark/light mode
- Press `q` or `Ctrl+C` to quit
- Check `sot_debug.log` for detailed logs

## 🧪 Code Quality

### Linting and Formatting

Before submitting changes, ensure your code passes quality checks:

#### Using Just (Recommended)
```sh
# Check code style and formatting
just lint

# Run type checking
just type

# Auto-fix type issues
just type-fix

# Auto-format code
just format
```

#### Manual Commands

**With uv:**
```sh
# Format code
uv run isort .
uv run black .
uv run blacken-docs README.md

# Run linting
uv run black --check .
uv run flake8 .

# Run type checking
uv run mypy src/sot

# Install missing type stubs
uv run mypy --install-types --non-interactive src/sot
```

**With pip:**
```sh
# Format code
isort .
black .
blacken-docs README.md

# Run linting
black --check .
flake8 .

# Run type checking
mypy src/sot

# Install missing type stubs
mypy --install-types --non-interactive src/sot
```

The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **blacken-docs** for documentation formatting

### Testing

Run the basic functionality test:

```sh
just dev
# Verify all widgets load and display correctly
# Test with different terminal sizes
# Check for any error messages
```

For more comprehensive testing:

```sh
# Test with specific network interface
python dev_runner.py --net eth0

# Test with debug logging
python dev_runner.py --debug --log test.log
```

## 📦 Adding Dependencies

### Using uv (Recommended)

For runtime dependencies:
```sh
uv add package-name
# Or using just
just uv-add package-name
```

For development dependencies:
```sh
uv add --dev package-name
# Or using just
just uv-add-dev package-name
```

This will automatically update `pyproject.toml` and `uv.lock`.

### Manual Method

1. **Runtime dependencies**: Add them to `pyproject.toml` under `dependencies`
2. **Development dependencies**: Add them to `pyproject.toml` under `[tool.uv] dev-dependencies`
3. Run `uv sync --dev` to install the new dependencies
4. Test that the dependency works correctly

### Dependency Guidelines

- Pin major versions for runtime dependencies (e.g., `requests>=2.25.0`)
- Be more specific with development tool versions for consistency
- Always test new dependencies across supported Python versions

## 📖 Man Page

SOT includes a man page that is automatically generated from the argparse configuration using `argparse-manpage`.

### Building the Man Page

The man page is built automatically as part of the build and publish process:

```sh
# Build just the man page
just build-man

# Or directly
uv run python scripts/build_manpage.py
```

The generated man page will be at `man/sot.1`.

### Testing the Man Page Locally

```sh
# Build and view the man page
just build-man
man ./man/sot.1
```

### Man Page Updates

The man page is automatically generated from:
- Command-line argument definitions in `src/sot/_app.py`
- Additional sections defined in `scripts/build_manpage.py`

**When to regenerate:**
- After adding/modifying CLI arguments
- After adding/removing subcommands
- Before publishing a new release (handled automatically)

**What's included:**
- Command synopsis and all options
- Subcommand documentation (info, bench, disk)
- Usage examples
- Feature descriptions
- Interactive controls
- See also references to similar tools

The man page is packaged in:
- **Source distribution (sdist)**: `man/sot.1`
- **Wheel**: `share/man/man1/sot.1` (auto-installed)
- **Homebrew**: Installed to `/usr/local/share/man/man1/sot.1` or `/opt/homebrew/share/man/man1/sot.1`

See `HOMEBREW_MANPAGE.md` for Homebrew-specific installation details.

## 🏗️ Project Structure

```sh
sot/                           # Root project directory
├── src/
│   ├── sot/                   # Main source code
│   │   ├── __about__.py
│   │   ├── __init__.py
│   │   ├── _app.py
│   │   ├── _cpu.py
│   │   ├── _disk.py
│   │   ├── _mem.py
│   │   ├── _net.py
│   │   ├── _procs_list.py
│   │   ├── _info.py
│   │   ├── _battery.py
│   │   ├── _helpers.py
│   │   ├── braille_stream.py
│   │   ├── blockchar_stream.py
│   │   └── _base_widget.py
│   └── dev/                   # 🆕 Development tools (not packaged)
│       ├── dev_runner.py      # 🆕 Development runner with descriptive names
│       ├── watch_dev.py       # 🆕 File watcher with signal handling
│       └── terminal_test.py   # 🆕 Terminal diagnostics
├── scripts/
│   └── build_manpage.py       # Man page generation script
├── man/
│   └── sot.1                  # Generated man page
├── .vscode/                   # VS Code configuration
│   ├──settings.json
│   └── launch.json            # Debug configurations
├── justfile
├── CONTRIBUTING.md
├── HOMEBREW_MANPAGE.md        # Homebrew man page documentation
├── pyproject.toml
├── .gitignore
├── README.md
├── LICENSE
└── tox.ini
```

### Color Scheme

SOT uses a consistent color palette:

| Color | Hex | Usage |
|-------|-----|-------|
| `sky_blue3` | `#5fafd7` | Primary highlights |
| `aquamarine3` | `#5fd7af` | Secondary highlights |
| `yellow` | `#808000` | Warnings/graphs |
| `bright_black` | `#808080` | Borders |
| `slate_blue1` | `#875fff` | Temperature data |
| `red3` | `#d70000` | Alerts/errors |
| `dark_orange` | `#d75f00` | High usage warnings |

### Common Issues

1. **Widget not updating:** Check if `self.refresh()` is called after data changes
2. **Layout problems:** Verify CSS grid settings and widget dimensions  
3. **Performance issues:** Use `set_interval()` with appropriate delays
4. **Import errors:** Ensure `PYTHONPATH` includes `src/`

### Logging

Add debug logging to your widgets:

```py
from textual import log

class MyWidget(Widget):
    def update_data(self):
        log("Updating widget data")
        # ... your code
```

## 📚 Resources

- [Textual Documentation](https://textual.textualize.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [psutil Documentation](https://psutil.readthedocs.io/)
- [SOT Architecture Overview](README.md#features)

## 🤝 Getting Help

- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/anistark/sot/issues)
- 💡 **Feature Requests:** [GitHub Discussions](https://github.com/anistark/sot/discussions)
- 💬 **Questions:** Feel free to open an issue with the `question` label

---

Happy coding! 🎉 Your contributions help make SOT better for everyone.
