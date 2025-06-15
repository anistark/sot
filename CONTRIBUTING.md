# SOT Contributing Guidelines

The SOT community appreciates your contributions via [issues](https://github.com/anistark/sot/issues) and [pull requests](https://github.com/anistark/sot/pulls).

When submitting pull requests, please follow the style guidelines of the project, ensure that your code is tested and documented, and write good commit messages, e.g., following [these guidelines](https://chris.beams.io/posts/git-commit/).

By submitting a pull request, you are licensing your code under the project [license](LICENSE) and affirming that you either own copyright (automatic for most individuals) or are authorized to distribute under the project license (e.g., in case your employer retains copyright on your work).

## Setup

### Prerequisites

```sh
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```sh
pip install -e .
```

### Set Up Development Environment

```sh
just setup-dev
```

This will install additional development dependencies like `watchdog` and `textual-dev` for hot reloading and advanced debugging.

## 🔧 Development Workflow

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

```sh
# Check code style and formatting
just lint

# Auto-format code
just format
```

The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
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
├── .vscode/                   # VS Code configuration
│   ├──settings.json
│   └── launch.json            # Debug configurations
├── justfile
├── CONTRIBUTING.md
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
