"""Caches of developer tools, and the large stores only worth reviewing.

A cache with a ``command`` is cleaned by its own tool when that's installed,
since the tool knows what is still referenced (``pnpm store prune``) or how
to remove files it made read-only (``go clean -modcache``). Without the tool
the paths are deleted instead.

``REVIEW`` lists stores that are expensive to get back or hold real work:
models, VM disks, toolchains, backups. They're measured and shown, never
deleted.
"""

from __future__ import annotations

from typing import NamedTuple


class DevCache(NamedTuple):
    name: str
    description: str
    paths: tuple[str, ...]
    command: tuple[str, ...] = ()
    env: dict[str, str] = {}


class Review(NamedTuple):
    name: str
    description: str
    paths: tuple[str, ...]


DEV_CACHES: tuple[DevCache, ...] = (
    DevCache(
        "Homebrew Cache",
        "Downloads and outdated versions",
        ("{mac_caches}/Homebrew", "{xdg_cache}/Homebrew"),
        ("brew", "cleanup", "--prune=all"),
    ),
    DevCache(
        "Go Cache",
        "Go module and build cache",
        (
            "{gomodcache}",
            "{gopath}/pkg/mod",
            "{gocache}",
            "{mac_caches}/go-build",
            "{xdg_cache}/go-build",
            "{localappdata}/go-build",
        ),
        ("go", "clean", "-cache", "-modcache"),
    ),
    DevCache(
        "pnpm Store",
        "Packages no project uses",
        (
            "{home}/Library/pnpm/store",
            "{xdg_data}/pnpm/store",
            "{localappdata}/pnpm/store",
            "{home}/.pnpm-store",
        ),
        ("pnpm", "store", "prune"),
    ),
    DevCache(
        "uv Cache",
        "Unused uv cache entries",
        ("{uv_cache}", "{xdg_cache}/uv", "{localappdata}/uv/cache"),
        ("uv", "cache", "prune"),
        # Prune waits for every running uv process, `uv run sot` included.
        {"UV_LOCK_TIMEOUT": "5"},
    ),
    DevCache(
        "Bun Cache",
        "Bun package cache",
        ("{bun_cache}", "{home}/.bun/install/cache"),
    ),
    DevCache(
        "Yarn Cache",
        "Yarn package cache",
        (
            "{mac_caches}/Yarn",
            "{xdg_cache}/yarn",
            "{home}/.yarn/berry/cache",
            "{localappdata}/Yarn/Cache",
        ),
    ),
    DevCache(
        "Cargo Cache",
        "Downloaded crates and git checkouts",
        (
            "{cargo_home}/registry/cache",
            "{cargo_home}/registry/src",
            "{cargo_home}/git/checkouts",
            "{rustup_home}/downloads",
            "{rustup_home}/tmp",
        ),
    ),
    DevCache(
        "Gradle Cache",
        "Gradle build cache and daemon logs",
        ("{gradle_home}/caches/build-cache-*", "{gradle_home}/daemon/*/*.log"),
    ),
    DevCache(
        "Android Cache",
        "Android SDK and build caches",
        ("{home}/.android/cache", "{home}/.android/build-cache"),
    ),
    DevCache(
        "Composer Cache",
        "PHP Composer cache",
        (
            "{home}/.composer/cache",
            "{mac_caches}/composer",
            "{xdg_cache}/composer",
            "{localappdata}/Composer",
        ),
    ),
    DevCache(
        "Xcode DerivedData",
        "Xcode build products and indexes",
        ("{home}/Library/Developer/Xcode/DerivedData",),
    ),
    DevCache(
        "Simulator Caches",
        "iOS Simulator caches, logs and test clones",
        (
            "{home}/Library/Developer/CoreSimulator/Caches",
            "{home}/Library/Developer/XCTestDevices",
            "{home}/Library/Logs/CoreSimulator",
        ),
    ),
)

REVIEW: tuple[Review, ...] = (
    Review(
        "Docker Disk",
        "Docker VM disk; see docker system df",
        (
            "{home}/Library/Containers/com.docker.docker/Data/vms",
            "{localappdata}/Docker/wsl",
        ),
    ),
    Review(
        "OrbStack Data",
        "OrbStack VM disk",
        ("{home}/Library/Group Containers/HUAQ24HBR6.dev.orbstack/data",),
    ),
    Review("Colima Disks", "Colima VM disks", ("{home}/.colima",)),
    Review(
        "Xcode Archives",
        "App archives with their crash symbols",
        ("{home}/Library/Developer/Xcode/Archives",),
    ),
    Review(
        "Simulators",
        "iOS Simulator devices; xcrun simctl erase",
        ("{home}/Library/Developer/CoreSimulator/Devices",),
    ),
    Review(
        "iOS Backups",
        "iPhone and iPad backups",
        ("{mac_app_support}/MobileSync/Backup", "{appdata}/Apple Computer/MobileSync"),
    ),
    Review(
        "Claude VM Bundles",
        "Claude desktop sandbox VM images",
        ("{mac_app_support}/Claude/vm_bundles",),
    ),
    Review(
        "Ollama Models",
        "Downloaded Ollama models",
        ("{ollama_models}", "{home}/.ollama/models"),
    ),
    Review(
        "LM Studio Models", "Downloaded LM Studio models", ("{home}/.lmstudio/models",)
    ),
    Review(
        "Hugging Face",
        "Hugging Face models and datasets",
        ("{hf_home}", "{xdg_cache}/huggingface"),
    ),
    Review(
        "Maven Repository", "Downloaded Maven artifacts", ("{home}/.m2/repository",)
    ),
    Review("Android Emulators", "Android virtual devices", ("{home}/.android/avd",)),
    Review(
        "Rust Toolchains", "Installed rustup toolchains", ("{rustup_home}/toolchains",)
    ),
    Review(
        "Node Versions",
        "Node.js versions from nvm, fnm and Volta",
        (
            "{nvm_dir}/versions/node",
            "{home}/.fnm/node-versions",
            "{home}/.volta/tools/image/node",
        ),
    ),
    Review(
        "Python Versions",
        "Python versions from pyenv and uv",
        ("{home}/.pyenv/versions", "{xdg_data}/uv/python"),
    ),
    Review(
        "Windows.old",
        "Previous Windows install; use Disk Cleanup",
        ("{systemdrive}/Windows.old",),
    ),
)
