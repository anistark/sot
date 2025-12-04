#!/usr/bin/env bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            OS_VERSION=$VERSION_ID
        else
            OS="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_VERSION=$(sw_vers -productVersion)
    else
        OS="unknown"
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    print_info "Checking for Python installation..."

    if command_exists python3; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            print_success "Python $PYTHON_VERSION found"
            return 0
        else
            print_error "Python 3.10+ required, found $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
}

# Install Python based on OS
install_python() {
    print_info "Installing Python 3..."

    case $OS in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3 python3-pip
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm python python-pip
            ;;
        macos)
            if command_exists brew; then
                brew install python@3.12
            else
                print_error "Homebrew not found. Please install Python 3.10+ manually from https://www.python.org/downloads/"
                exit 1
            fi
            ;;
        *)
            print_error "Unable to auto-install Python on $OS. Please install Python 3.10+ manually."
            exit 1
            ;;
    esac

    if check_python; then
        print_success "Python installed successfully"
    else
        print_error "Python installation failed"
        exit 1
    fi
}

# Check if pipx is installed
check_pipx() {
    if command_exists pipx; then
        print_success "pipx found"
        return 0
    else
        print_info "pipx not found"
        return 1
    fi
}

# Install pipx
install_pipx() {
    print_info "Installing pipx..."

    if ! check_python; then
        install_python
    fi

    # Install pipx using pip
    $PYTHON_CMD -m pip install --user pipx

    # Ensure pipx is in PATH
    $PYTHON_CMD -m pipx ensurepath

    # Source the shell config to update PATH in current session
    if [ -f "$HOME/.bashrc" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    elif [ -f "$HOME/.zshrc" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if check_pipx; then
        print_success "pipx installed successfully"
    else
        print_warning "pipx installed but not in PATH. Please restart your shell or run:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        exit 1
    fi
}

# Install sot using pipx
install_sot() {
    print_info "Installing sot via pipx..."

    if pipx install sot; then
        print_success "sot installed successfully!"
        return 0
    else
        print_error "Failed to install sot"
        return 1
    fi
}

# Verify installation
verify_installation() {
    print_info "Verifying installation..."

    if command_exists sot; then
        SOT_VERSION=$(sot --version 2>&1 | head -1)
        print_success "Installation verified: $SOT_VERSION"
        return 0
    else
        print_warning "sot command not found in PATH"
        print_info "You may need to restart your shell or run:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        return 1
    fi
}

# Main installation flow
main() {
    echo ""
    echo "════════════════════════════════════"
    echo "  Thanks for trying out SOT"
    echo "  System Observation Tool"
    echo "════════════════════════════════════"
    echo ""

    detect_os
    print_info "Detected OS: $OS"

    # Check and install Python if needed
    if ! check_python; then
        print_warning "Python 3.10+ is required"
        read -p "Would you like to install Python? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_python
        else
            print_error "Python is required to continue"
            exit 1
        fi
    fi

    # Check and install pipx if needed
    if ! check_pipx; then
        print_warning "pipx is required for installation"
        read -p "Would you like to install pipx? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_pipx
        else
            print_error "pipx is required to continue"
            exit 1
        fi
    fi

    # Install sot
    if install_sot; then
        echo ""
        print_success "════════════════════════════════════════"
        print_success "  Installation completed successfully!"
        print_success "════════════════════════════════════════"
        echo ""

        if verify_installation; then
            print_info "Run 'sot' to start the application"
        else
            print_warning "Please restart your shell and then run 'sot'"
        fi
        echo ""
    else
        print_error "Installation failed"
        exit 1
    fi
}

# Run main function
main
