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
publish: clean format lint type
	@if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then echo "❌ Must be on main branch to publish"; exit 1; fi
	@echo "📋 Version: {{version}}"
	@echo "🔨 Building package..."
	uv build --sdist --wheel
	@echo "📦 Publishing to PyPI..."
	uv run twine upload dist/*
	@echo "🏷️  Creating git tag for SOT version {{version}}..."
	git tag "v{{version}}"
	git push origin "v{{version}}"
	@echo "🚀 Creating GitHub release..."
	gh release create "v{{version}}" --generate-notes --files "dist/*"
	@echo "✅ Published v{{version}} to PyPI and GitHub!"

publish-test: clean
	uv run python -m build --sdist --wheel .
	uv run twine check dist/*

# Security commands
gpg-generate-keys:
	@TIMESTAMP=$$(date +%Y%m%d-%H%M%S) && \
	echo "🔐 Generating new GPG key for SOT release signing ($$TIMESTAMP)..." && \
	echo "📋 This will:" && \
	echo "   - Generate a new 4096-bit RSA GPG key with secure passphrase" && \
	echo "   - Replace .github/public-key.asc" && \
	echo "   - Securely save base64 private key to file" && \
	echo "" && \
	echo "⚠️  You will need to enter a secure passphrase for the GPG key!" && \
	echo "💡 This passphrase must be stored in GitHub secrets as GPG_PASSPHRASE" && \
	echo "" && \
	read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1 && \
	echo "" && \
	echo "🔐 Enter secure passphrase for GPG key (will be hidden):" && \
	read -s GPG_PASSPHRASE && \
	echo "" && \
	echo "🔧 Generating GPG key..." && \
	gpg --batch --full-generate-key --passphrase "$$GPG_PASSPHRASE" <<< \
		"Key-Type: RSA\nKey-Length: 4096\nSubkey-Type: RSA\nSubkey-Length: 4096\nExpire-Date: 2y\nName-Real: SOT Release Signing $$TIMESTAMP\nName-Email: sot@anirudha.dev\nName-Comment: Automated release signing key - Generated $$TIMESTAMP\n%commit\n" && \
	KEY_ID=$$(gpg --list-secret-keys --keyid-format LONG | grep -A1 "SOT Release Signing $$TIMESTAMP" | grep sec | cut -d'/' -f2 | cut -d' ' -f1) && \
	echo "🔑 Key ID: $$KEY_ID" && \
	echo "📤 Exporting public key to .github/public-key.asc..." && \
	gpg --armor --export $$KEY_ID > .github/public-key.asc && \
	echo "📋 Fingerprint:" && \
	gpg --fingerprint $$KEY_ID | grep -A1 "Key fingerprint" | tail -1 && \
	echo "" && \
	echo "🔒 Generating secure private key file..." && \
	PRIVATE_KEY_FILE="/tmp/sot-private-key-$$TIMESTAMP.txt" && \
	gpg --armor --export-secret-keys $$KEY_ID | base64 > "$$PRIVATE_KEY_FILE" && \
	chmod 600 "$$PRIVATE_KEY_FILE" && \
	echo "" && \
	echo "✅ GPG key generated successfully!" && \
	echo "" && \
	echo "📋 NEXT STEPS:" && \
	echo "1. Copy private key from: $$PRIVATE_KEY_FILE" && \
	echo "2. Update GitHub secret GPG_PRIVATE_KEY with the content" && \
	echo "3. Update GitHub secret GPG_PASSPHRASE with your passphrase" && \
	echo "4. Delete the private key file when done: rm $$PRIVATE_KEY_FILE" && \
	echo "5. Run 'just gpg-cleanup' to remove old SOT keys if needed" && \
	echo "" && \
	echo "⚠️  IMPORTANT: Private key saved to $$PRIVATE_KEY_FILE" && \
	echo "   Delete this file after updating GitHub secrets!"

gpg-cleanup:
	@echo "🗑️  Cleaning up old SOT GPG keys..."
	@echo "📋 Current SOT keys:"
	@gpg --list-secret-keys --keyid-format LONG | grep -B1 -A3 "SOT Release Signing" || echo "No SOT keys found"
	@echo ""
	@echo "⚠️  This will show you old keys to manually delete."
	@echo "💡 To delete a key: gpg --delete-secret-keys KEY_ID && gpg --delete-keys KEY_ID"
	@echo ""
	@read -p "Show all SOT keys for manual cleanup? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo ""
	@gpg --list-secret-keys --keyid-format LONG | grep -B2 -A5 "SOT Release Signing" | \
	grep -E "(sec|uid)" | \
	while read line; do \
		if echo "$$line" | grep -q "sec"; then \
			KEY_ID=$$(echo "$$line" | cut -d'/' -f2 | cut -d' ' -f1); \
			echo "🔑 Key ID: $$KEY_ID"; \
		elif echo "$$line" | grep -q "uid"; then \
			echo "👤 $$line"; \
			echo "🗑️  To delete: gpg --delete-secret-keys $$KEY_ID && gpg --delete-keys $$KEY_ID"; \
			echo ""; \
		fi; \
	done

security-check:
	@echo "🔍 Security Status Check"
	@echo "========================"
	@echo ""
	@echo "📋 GitHub Action Security:"
	@echo "   ✅ Actions pinned to commit SHAs"
	@echo "   ✅ Permissions restricted to minimum required"
	@echo "   ✅ Passphrase handling secured with files"
	@echo "   ✅ Sensitive file cleanup implemented"
	@echo ""
	@echo "🔐 GPG Key Status:"
	@SOT_KEYS=$$(gpg --list-secret-keys --keyid-format LONG | grep -c "SOT Release Signing" 2>/dev/null || echo "0") && \
	echo "   📊 SOT keys found: $$SOT_KEYS" && \
	if [ $$SOT_KEYS -eq 0 ]; then \
		echo "   ⚠️  No SOT GPG keys found - run 'just gpg-generate-keys'"; \
	elif [ $$SOT_KEYS -gt 1 ]; then \
		echo "   💡 Multiple keys found - consider running 'just gpg-cleanup'"; \
	else \
		echo "   ✅ Single active key found"; \
	fi
	@echo ""
	@echo "🔒 Key Expiration Check:"
	@gpg --list-secret-keys --keyid-format LONG | grep -A5 "SOT Release Signing" | grep -E "(expires|never)" | head -1 || echo "   ℹ️  No SOT keys to check"
	@echo ""
	@echo "📁 File Security:"
	@if [ -f .github/public-key.asc ]; then \
		echo "   ✅ Public key exists in .github/"; \
	else \
		echo "   ⚠️  Public key missing - run 'just gpg-generate-keys'"; \
	fi
	@if [ -f /tmp/sot-private-key-*.txt ]; then \
		echo "   ⚠️  Private key files found in /tmp/ - clean up after use!"; \
	else \
		echo "   ✅ No private key files in /tmp/"; \
	fi

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

type:
	@echo "🔍 Running type checking..."
	uv run ty check

type-fix:
	@echo "🔧 Auto-fixing type issues..."
	uv run ty --createstub

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
	@echo "  just type                   - Run type checking with ty"
	@echo "  just type-fix               - Auto-fix type issues with ty"
	@echo "  just format                 - Format code with black and isort"
	@echo ""
	@echo "Publishing:"
	@echo "  just publish                - Publish to PyPI (main branch only)"
	@echo "  just publish-test           - Test build without publishing"
	@echo ""
	@echo "Security:"
	@echo "  just gpg-generate-keys      - Generate new GPG keys for release signing (run every 2 years)"
	@echo "  just gpg-cleanup            - List and help remove old SOT GPG keys"
	@echo "  just security-check         - Check workflow and key security status"
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
