# Justfile for SOT (System Obversation Tool) project

version := `python3 -c "import sys; sys.path.insert(0, 'src'); from sot.__about__ import __version__; print(__version__)" 2>/dev/null || echo "dev"`

default:
	just help

# Development commands
version:
	@echo "🎯 SOT Version Information:"
	uv run python src/dev/dev_runner.py --version

dev:
	@echo "🚀 Starting SOT in development mode..."
	uv run python src/dev/dev_runner.py --debug

dev-watch:
	@echo "👀 Starting SOT with file watching..."
	@just install-dev-deps
	uv run python src/dev/watch_dev.py

dev-debug:
	@echo "🐛 Starting SOT with debug logging..."
	uv run python src/dev/dev_runner.py --debug --log sot_debug.log
	@echo "📋 Debug log saved to sot_debug.log"

dev-net INTERFACE:
	@echo "📡 Starting SOT with network interface: {{INTERFACE}}"
	uv run python src/dev/dev_runner.py --debug --net {{INTERFACE}}

dev-full INTERFACE LOG_FILE:
	@echo "🚀 Starting SOT with interface {{INTERFACE}} and logging to {{LOG_FILE}}"
	uv run python src/dev/dev_runner.py --debug --net {{INTERFACE}} --log {{LOG_FILE}}

terminal-test:
	@echo "🔍 Testing terminal compatibility..."
	uv run python src/dev/terminal_test.py

network-discovery:
	@echo "📡 Discovering available network interfaces..."
	uv run python src/dev/network_discovery.py

dev-console:
	@echo "🕹️  Starting SOT with Textual console..."
	@just install-dev-deps
	@echo "🔍 Run 'textual console' in another terminal for debugging"
	uv run python src/dev/dev_runner.py --debug

install-dev-deps:
	@echo "📦 Installing SOT in development mode with uv..."
	uv sync --dev
	uv pip install -e .

# uv-specific commands
uv-sync:
	@echo "🔄 Syncing dependencies with uv..."
	uv sync

uv-sync-dev:
	@echo "🔄 Syncing dev dependencies with uv..."
	uv sync --dev

uv-lock:
	@echo "🔒 Generating uv.lock file..."
	uv lock

uv-add PACKAGE:
	@echo "➕ Adding package {{PACKAGE}} with uv..."
	uv add {{PACKAGE}}

uv-add-dev PACKAGE:
	@echo "➕ Adding dev package {{PACKAGE}} with uv..."
	uv add --dev {{PACKAGE}}

uv-remove PACKAGE:
	@echo "➖ Removing package {{PACKAGE}} with uv..."
	uv remove {{PACKAGE}}

uv-tree:
	@echo "🌳 Showing dependency tree..."
	uv tree

setup-dev: install-dev-deps
	@echo "✅ Development environment ready!"
	@echo "💡 Run 'just dev-watch' to start coding with hot reload"
	@echo "🔍 Version: $(python3 -c "import sys; sys.path.insert(0, 'src'); from sot.__about__ import __version__; print(__version__)")"

# Publishing commands
publish: clean format lint
	@echo "🚀 Publishing SOT to PyPI..."
	@if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then exit 1; fi
	gh release create "v{{version}}"
	uv run python -m build --sdist --wheel .
	uv run twine upload dist/*

publish-test: clean
	uv run python -m build --sdist --wheel .
	uv run twine check dist/*

# Maintenance commands
clean:
	@echo "🧹 Cleaning up..."
	@find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
	@rm -rf src/*.egg-info/ build/ dist/ .tox/
	@rm -f sot_debug.log
	@rm -f *.svg
	@rm -f .coverage

format:
	@echo "✨ Formatting code..."
	uv run isort .
	uv run black .
	uv run blacken-docs README.md

lint:
	@echo "🔍 Running linting..."
	uv run black --check .
	uv run flake8 .

# Help command
help:
	@echo "🔧 SOT Development Commands:"
	@echo ""
	@echo "Info:"
	@echo "  just version                - Show detailed version information"
	@echo ""
	@echo "Development:"
	@echo "  just dev                    - Run SOT in development mode"
	@echo "  just dev-watch              - Run SOT with auto-restart on file changes"
	@echo "  just dev-debug              - Run SOT with debug logging"
	@echo "  just dev-net INTERFACE      - Run SOT with specific network interface"
	@echo "  just dev-full IF LOG        - Run SOT with interface and log file"
	@echo "  just dev-console            - Run SOT with textual console for debugging"
	@echo "  just terminal-test          - Test terminal compatibility and performance"
	@echo "  just network-discovery      - List available network interfaces"
	@echo "  just setup-dev              - Set up development environment"
	@echo ""
	@echo "UV Package Management:"
	@echo "  just uv-sync                - Sync dependencies with uv"
	@echo "  just uv-sync-dev            - Sync dev dependencies with uv"
	@echo "  just uv-lock                - Generate uv.lock file"
	@echo "  just uv-add PACKAGE         - Add package with uv"
	@echo "  just uv-add-dev PACKAGE     - Add dev package with uv"
	@echo "  just uv-remove PACKAGE      - Remove package with uv"
	@echo "  just uv-tree                - Show dependency tree"
	@echo ""
	@echo "Code Quality:"
	@echo "  just lint                   - Run linting (black + flake8)"
	@echo "  just format                 - Format code with black and isort"
	@echo ""
	@echo "Publishing:"
	@echo "  just publish                - Publish to PyPI (main branch only)"
	@echo "  just publish-test           - Test build without publishing"
	@echo ""
	@echo "Maintenance:"
	@echo "  just clean                  - Clean up development files"
	@echo "  just help                   - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  just dev-net eth0           - Use ethernet interface eth0"
	@echo "  just dev-full wlan0 debug.log - Use wlan0 with logging"
	@echo "  just uv-add requests        - Add requests package"
	@echo "  just uv-add-dev pytest     - Add pytest as dev dependency"
