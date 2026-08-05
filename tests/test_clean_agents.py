from pathlib import Path

from sot.clean import agents


def test_roots_fall_back_to_home_defaults():
    roots = agents.resolve_roots({})
    home = Path.home()
    assert roots["home"] == home
    assert roots["xdg_cache"] == home / ".cache"
    assert roots["claude_config"] == home / ".claude"
    # No default and no variable set, so the root is unavailable.
    assert "vscode_portable" not in roots


def test_env_overrides_root():
    roots = agents.resolve_roots({"CLAUDE_CONFIG_DIR": "/data/claude"})
    assert roots["claude_config"] == Path("/data/claude")
    # Unrelated roots keep their defaults.
    assert roots["xdg_cache"] == Path.home() / ".cache"


def test_blank_env_var_is_ignored():
    # An exported-but-empty variable must not resolve to the filesystem root.
    roots = agents.resolve_roots({"XDG_CACHE_HOME": "   "})
    assert roots["xdg_cache"] == Path.home() / ".cache"


def test_agent_paths_expand_against_roots():
    roots = agents.resolve_roots({"XDG_CACHE_HOME": "/scratch"})
    opencode = next(a for a in agents.CODING_AGENTS if a.name == "opencode Cache")
    assert Path("/scratch/opencode") in agents.agent_paths(opencode, roots)


def test_paths_needing_missing_root_are_skipped():
    kilo = next(a for a in agents.CODING_AGENTS if a.name == "Kilo Cache")
    without = agents.agent_paths(kilo, agents.resolve_roots({}))
    with_portable = agents.agent_paths(
        kilo, agents.resolve_roots({"VSCODE_PORTABLE": "/opt/vscode"})
    )
    # The two portable-mode templates only expand once the variable is set.
    assert len(with_portable) == len(without) + 2
    assert not any("vscode" in str(p).lower() for p in without)


def test_every_template_uses_a_known_root():
    roots = agents.resolve_roots({})
    known = set(agents.CACHE_ROOTS)
    for agent in agents.CODING_AGENTS:
        for template in agent.paths:
            root = template.split("}", 1)[0].lstrip("{")
            assert root in known, f"{agent.name}: unknown root {root!r}"
        # Nothing may expand to a bare root, which would wipe the directory.
        for path in agents.agent_paths(agent, roots):
            assert path not in roots.values(), f"{agent.name}: {path} is a root"
