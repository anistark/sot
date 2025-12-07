# Homebrew Man Page Installation

The man page for `sot` is automatically included in the Python package (sdist and wheel).

## For Homebrew Formula Maintainers

The man page is automatically included in the Python wheel under `share/man/man1/sot.1`. When installing via Homebrew with `virtualenv_install_with_resources`, the man page will be installed automatically to the correct location.

If you need to explicitly install it, add the following to the `sot.rb` formula in the `homebrew-tools` repository:

```ruby
class Sot < Formula
  include Language::Python::Virtualenv

  desc "Command-line System Observation Tool"
  homepage "https://github.com/anistark/sot"
  url "https://files.pythonhosted.org/packages/.../sot-X.Y.Z.tar.gz"
  sha256 "..."

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources

    # Man page is included in the wheel and installed automatically
    # If needed, you can also install from the source tarball:
    # man1.install "man/sot.1"
  end

  test do
    system "#{bin}/sot", "--version"
    # Verify man page is installed
    system "man", "#{man1}/sot.1"
  end
end
```

**Note:** The man page is now packaged in both:
- **Source distribution (sdist)**: `man/sot.1`
- **Wheel**: `share/man/man1/sot.1` (installed automatically via pip/virtualenv)

## Manual Installation of Man Page

If you want to install the man page manually on your system:

```bash
# Build the man page
just build-man

# Copy to system man directory (requires sudo)
sudo cp man/sot.1 /usr/local/share/man/man1/

# Update man database
sudo mandb  # Linux
# or
sudo /usr/libexec/makewhatis /usr/local/share/man  # macOS
```

## Testing Man Page Locally

To test the man page without installing it:

```bash
# Build the man page
just build-man

# View it directly
man ./man/sot.1
```

## Man Page Generation

The man page is automatically generated from the argparse configuration using `argparse-manpage`. To regenerate:

```bash
just build-man
# or
uv run python scripts/build_manpage.py
```

The generated man page includes:
- Command synopsis and options
- Subcommand documentation (info, bench, disk)
- Examples
- Feature descriptions
- Interactive controls
- See also references
- Bug reporting information
