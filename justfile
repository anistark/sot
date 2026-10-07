# Justfile for SOT (System Obversation Tool) project

version := `grep '__version__' src/sot/__about__.py | sed 's/.*"\([^"]*\)".*/\1/'`

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

# Run SOT with arguments
sot *ARGS:
	@echo "📦 Installing SOT..."
	uv pip install .
	@echo "🚀 Running SOT..."
	uv run sot {{ARGS}}

# Build man page
build-man:
	@echo "📖 Building man page..."
	uv run python scripts/build_manpage.py
	@echo "✅ Man page built successfully!"

# Build SOT locally
build: build-man
	@echo "🔨 Building SOT locally..."
	uv pip install .
	@echo "✅ SOT built successfully!"

# Install SOT system-wide
install:
	@echo "🌍 Installing SOT system-wide..."
	uv pip install --system --break-system-packages .
	@echo "✅ SOT installed system-wide!"
	@echo "🚀 You can now run 'sot' from anywhere"

# Uninstall SOT from system and local
uninstall:
	@echo "🗑️  Uninstalling SOT..."
	@echo "📋 Removing system-wide installation..."
	-uv pip uninstall --system sot -y
	@echo "📋 Removing local installation..."
	-pip uninstall sot -y
	@echo "🧹 Cleaning up development files..."
	@just clean
	@echo "✅ SOT uninstalled successfully!"

install-dev-deps:
	@echo "📦 Installing SOT in development mode with uv..."
	uv sync --dev
	uv pip install -e .

setup-dev: install-dev-deps
	@echo "✅ Development environment ready!"
	@echo "💡 Run 'just dev-watch' to start coding with hot reload"
	@echo "🔍 Version: $(python3 -c "import sys; sys.path.insert(0, 'src'); from sot.__about__ import __version__; print(__version__)")"

# Publishing commands
# Runs pre-flight checks and pushes the version tag. The Publish workflow
# (.github/workflows/publish.yml) then builds, publishes to PyPI via Trusted
# Publishing, and creates the GitHub release.
publish: clean lint type test build-man
	@if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then echo "❌ Must be on main branch to publish"; exit 1; fi
	@if [ -n "$(git status --porcelain)" ]; then echo "❌ Working tree is dirty, commit or stash first"; git status --short; exit 1; fi
	@git fetch origin main --quiet
	@if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then echo "❌ Local main is not in sync with origin/main"; exit 1; fi
	@if git rev-parse -q --verify "refs/tags/v{{version}}" >/dev/null || git ls-remote --exit-code --tags origin "v{{version}}" >/dev/null; then echo "❌ Tag v{{version}} already exists, bump the version first"; exit 1; fi
	@echo "📋 Version: {{version}}"
	@just publish-test
	@echo "🏷️  Creating git tag for SOT version {{version}}..."
	git tag -a "v{{version}}" -m "v{{version}}"
	git push origin "v{{version}}"
	@echo "✅ Pushed v{{version}}. Approve the 'pypi' deployment in GitHub Actions to publish:"
	@echo "   https://github.com/anistark/sot/actions/workflows/publish.yml"

# Build and validate distributions without publishing
publish-test: clean build-man
	uv build
	uvx twine check --strict dist/*

# Security commands
security-check:
	@echo "🔍 Security Status Check"
	@echo "========================"
	@echo ""
	@echo "📋 GitHub Actions pinned to commit SHAs:"
	@UNPINNED=$(grep -hE '^[[:space:]]*(- )?uses:[[:space:]]+[^.]' .github/workflows/*.yml | grep -vE '@[0-9a-f]{40}' || true); \
	if [ -n "$UNPINNED" ]; then echo "   ⚠️  Unpinned actions:"; echo "$UNPINNED" | sed 's/^[[:space:]]*/      /'; else echo "   ✅ All actions pinned"; fi
	@echo ""
	@echo "🔐 PyPI publishing:"
	@if grep -q "id-token: write" .github/workflows/publish.yml 2>/dev/null; then echo "   ✅ Trusted Publishing workflow present"; else echo "   ⚠️  publish.yml missing or lacks id-token: write"; fi
	@if grep -q "^\[pypi\]" ~/.pypirc 2>/dev/null; then echo "   ⚠️  ~/.pypirc holds a PyPI token, revoke it once Trusted Publishing works"; else echo "   ✅ No PyPI token in ~/.pypirc"; fi

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

type: lint
	@echo "🔍 Running type checking..."
	uv run mypy src/sot

type-fix:
	@echo "🔧 Installing missing type stubs..."
	uv run mypy --install-types --non-interactive src/sot

test:
	@echo "🧪 Running tests..."
	uv run pytest tests

# Help command
help:
	@echo "🔧 SOT Development Commands:"
	@echo ""
	@echo "Quick Start:"
	@echo "  just sot                    - Install and run SOT"
	@echo "  just sot --help             - Show SOT help"
	@echo "  just sot bench              - Run disk benchmarking"
	@echo "  just sot bench --help       - Show benchmark help"
	@echo ""
	@echo "Installation:"
	@echo "  just build-man              - Build man page"
	@echo "  just build                  - Build SOT locally (includes man page)"
	@echo "  just install                - Install SOT system-wide"
	@echo "  just uninstall              - Uninstall SOT from system and local"
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
	@echo "Code Quality:"
	@echo "  just lint                   - Run linting (black + flake8)"
	@echo "  just type                   - Run type checking with mypy"
	@echo "  just type-fix               - Install missing type stubs with mypy"
	@echo "  just format                 - Format code with black and isort"
	@echo "  just test                   - Run the test suite"
	@echo ""
	@echo "Publishing:"
	@echo "  just publish                - Check and push a release tag; CI publishes to PyPI"
	@echo "  just publish-test           - Build and validate distributions without publishing"
	@echo ""
	@echo "Security:"
	@echo "  just security-check         - Check action pinning and PyPI publishing setup"
	@echo ""
	@echo "Maintenance:"
	@echo "  just clean                  - Clean up development files"
	@echo "  just help                   - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  just dev-net eth0           - Use ethernet interface eth0"
	@echo "  just dev-full wlan0 debug.log - Use wlan0 with logging"
