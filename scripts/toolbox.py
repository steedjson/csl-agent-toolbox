#!/usr/bin/env python3
"""List, update, and install csl-agent-toolbox components with host-native adapters."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import install_skills
import sync_upstream

REPO = Path(__file__).resolve().parent.parent
MCP_HOSTS = {"codex", "claude", "pi", "omp"}


def catalog(repo):
    return json.loads((repo / "skills.json").read_text(encoding="utf-8"))


def component(repo, kind, name):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise ValueError(f"invalid component name: {name!r}")
    key, _ = sync_upstream.COMPONENTS[kind]
    entry = next((e for e in catalog(repo).get(key, []) if e["name"] == name), None)
    if entry is None:
        raise ValueError(f"unknown {kind}: {name}")
    root = sync_upstream.component_dir(repo, name, kind)
    if not root.is_dir() or not root.resolve().is_relative_to(repo.resolve()):
        raise ValueError(f"component directory missing or outside repository: {kind}/{name}")
    return entry, root


def mcp_server(root, name):
    data = json.loads((root / "mcp.json").read_text(encoding="utf-8"))
    servers = data.get("mcpServers", {})
    if set(servers) != {name}:
        raise ValueError(f"{root}/mcp.json must contain exactly mcpServers.{name}")
    server = servers[name]
    if not isinstance(server, dict):
        raise ValueError("MCP server must be an object")
    allowed = {"type", "command", "args", "env", "url", "headers", "bearer_token_env_var"}
    if set(server) - allowed:
        raise ValueError(f"unsupported MCP fields: {', '.join(sorted(set(server) - allowed))}")
    transport = server.get("type", "http" if "url" in server else "stdio")
    if transport not in {"stdio", "http", "streamable-http"}:
        raise ValueError(f"unsupported MCP transport: {transport}")
    if transport == "stdio":
        if not isinstance(server.get("command"), str) or not server["command"]:
            raise ValueError("stdio MCP requires command")
        if "url" in server or "headers" in server or "bearer_token_env_var" in server:
            raise ValueError("stdio MCP cannot contain HTTP fields")
    elif not isinstance(server.get("url"), str) or not server["url"].startswith(("https://", "http://")):
        raise ValueError("HTTP MCP requires an http(s) URL")
    elif any(field in server for field in ("command", "args", "env")):
        raise ValueError("HTTP MCP cannot contain stdio fields")
    if not isinstance(server.get("args", []), list) or not all(isinstance(x, str) for x in server.get("args", [])):
        raise ValueError("MCP args must be a string array")
    for field in ("env", "headers"):
        if not isinstance(server.get(field, {}), dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in server.get(field, {}).items()
        ):
            raise ValueError(f"MCP {field} must map strings to strings")
    token = server.get("bearer_token_env_var")
    if token is not None and (not isinstance(token, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token)):
        raise ValueError("bearer_token_env_var must be an environment variable name")
    return {**server, "type": "http" if transport == "streamable-http" else transport}


def expand(value, repo, root):
    """Resolve local paths and secret references only when explicitly installing."""
    if isinstance(value, dict):
        return {key: expand(item, repo, root) for key, item in value.items()}
    if isinstance(value, list):
        return [expand(item, repo, root) for item in value]
    if not isinstance(value, str):
        return value
    variables = {**os.environ, "TOOLBOX_ROOT": str(repo), "COMPONENT_ROOT": str(root)}

    def replace(match):
        key = match.group(1)
        if key not in variables:
            raise ValueError(f"required environment variable is unset: {key}")
        return variables[key]

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, value)


def mcp_commands(host, name, server, remove=False):
    if host not in MCP_HOSTS:
        raise ValueError(f"{host}: MCP adapter unavailable; supported: {', '.join(sorted(MCP_HOSTS))}")
    if host == "omp":
        return []  # OMP has a native config file, but no noninteractive add/remove CLI.
    if remove:
        return [[host, "mcp", "remove", *(["--scope", "user"] if host == "claude" else []), name]]
    if host == "claude":
        config = dict(server)
        token = config.pop("bearer_token_env_var", None)
        if token:
            config.setdefault("headers", {})["Authorization"] = "Bearer ${" + token + "}"
        return [["claude", "mcp", "add-json", "--scope", "user", name, json.dumps(config)]]
    args = [host, "mcp", "add", name]
    if server["type"] == "http":
        if host == "codex" and server.get("headers"):
            raise ValueError(f"{host}: custom HTTP headers are not supported by this adapter")
        args += ["--url", server["url"]]
        for key, value in server.get("headers", {}).items():
            args += ["--header", f"{key}={value}"]
        token = server.get("bearer_token_env_var")
        if token:
            args += ["--bearer-token-env-var", token]
    else:
        for key, value in server.get("env", {}).items():
            args += ["--env", f"{key}={value}"]
        args += ["--", server["command"], *server.get("args", [])]
    return [args]


def omp_config_path():
    config = Path(os.environ.get("PI_CONFIG_DIR", "~/.omp")).expanduser()
    base = Path(os.environ.get("PI_CODING_AGENT_DIR", str(config / "agent"))).expanduser()
    return base / "mcp.json"


def read_mcp_config(path):
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
        raise ValueError(f"invalid native MCP configuration: {path}")
    return data


def mcp_exists(host, name):
    if host in {"codex", "claude"}:
        result = subprocess.run([host, "mcp", "get", name], capture_output=True, text=True, timeout=30)
        if result.returncode and not re.search(r"(no .*(server|configuration)|not found|does not exist)", result.stdout + result.stderr, re.I):
            raise ValueError(f"{host}: unable to inspect existing MCP configuration")
        return result.returncode == 0
    if host == "pi":
        root = Path(os.environ.get("PI_CODING_AGENT_DIR", "~/.pi/agent")).expanduser()
        path = root / "mcp.json"
    else:
        path = omp_config_path()
    return name in read_mcp_config(path).get("mcpServers", {})


def write_omp_mcp(name, server, remove):
    path = omp_config_path().resolve()
    data = read_mcp_config(path)
    servers = data.setdefault("mcpServers", {})
    if remove:
        if name not in servers:
            return
        del servers[name]
    else:
        if name in servers:
            raise ValueError(f"omp: MCP {name} already exists; remove or rename it first")
        config = dict(server)
        token = config.pop("bearer_token_env_var", None)
        if token:
            config.setdefault("headers", {})["Authorization"] = f"Bearer {os.environ[token]}"
        servers[name] = config
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".toolbox-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def plugin_commands(repo, root, host, name, remove):
    package = root / "package.json"
    if host in {"pi", "omp"} and package.is_file():
        metadata = json.loads(package.read_text())
        if not isinstance(metadata.get("name"), str) or not metadata["name"]:
            raise ValueError(f"{host}: native package requires package.json.name")
        if host == "pi" and isinstance(metadata.get("pi"), dict):
            return [["pi", "remove" if remove else "install", str(root)]]
        if host == "omp" and any(isinstance(metadata.get(key), dict) for key in ("omp", "pi")):
            return [["omp", "plugin", "uninstall", metadata["name"]]] if remove else [["omp", "plugin", "link", str(root)]]
    if host == "codex" and ((root / ".codex-plugin/plugin.json").is_file() or (root / "plugin.json").is_file()):
        marketplace = json.loads((repo / ".agents/plugins/marketplace.json").read_text())
        entries = marketplace.get("plugins", [])
        entry = next((item for item in entries if item.get("name") == name), None)
        if not entry or (repo / entry.get("source", {}).get("path", "")).resolve() != root.resolve():
            raise ValueError(f"{name}: add this plugin to .agents/plugins/marketplace.json first")
        selector = f"{name}@{marketplace['name']}"
        if remove:
            return [["codex", "plugin", "remove", selector]]
        return [["codex", "plugin", "marketplace", "add", str(repo)], ["codex", "plugin", "add", selector]]
    if host == "claude" and (root / ".claude-plugin/plugin.json").is_file():
        marketplace = json.loads((repo / ".claude-plugin/marketplace.json").read_text())
        if not any(item.get("name") == name and (repo / item.get("source", "")).resolve() == root.resolve()
                   for item in marketplace.get("plugins", [])):
            raise ValueError(f"{name}: missing Claude marketplace entry")
        selector = f"{name}@{marketplace['name']}"
        if remove:
            return [["claude", "plugin", "uninstall", "--scope", "user", selector]]
        return [["claude", "plugin", "marketplace", "add", str(repo), "--scope", "user"],
                ["claude", "plugin", "install", "--scope", "user", selector]]
    raise ValueError(f"{host}: {name} has no supported native plugin package; automatic format conversion is unavailable")


def run_commands(commands):
    for command in commands:
        # Native commands can contain credentials. Print identity, never argument values or captured output.
        print(f"native: {' '.join(command[:3])}")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f"native command failed ({result.returncode}): {' '.join(command[:3])}; check the host CLI")


def install(args):
    if not args.host:
        raise ValueError("install/uninstall requires --host; --host agents explicitly selects shared user-level skills")
    if not (args.skill or args.mcp or args.plugin):
        raise ValueError("select one or more --skill, --mcp, or --plugin")
    for host in args.host:
        if host not in install_skills.HOSTS:
            raise ValueError(f"unknown host: {host}")
    remove = args.command == "uninstall"
    jobs = []
    for kind in ("skill", "mcp", "plugin"):
        for name in dict.fromkeys(getattr(args, kind)):
            _, root = component(REPO, kind, name)
            for host in dict.fromkeys(args.host):
                server = None
                if kind == "skill":
                    commands = []
                elif kind == "mcp":
                    server = mcp_server(root, name)
                    commands = mcp_commands(host, name, server, remove)
                else:
                    commands = plugin_commands(REPO, root, host, name, remove)
                if not args.dry_run and kind != "skill":
                    for command in commands:
                        if shutil.which(command[0]) is None:
                            raise ValueError(f"required host CLI unavailable: {command[0]}")
                    if kind == "mcp":
                        exists = mcp_exists(host, name)
                        if not remove and exists:
                            raise ValueError(f"{host}: MCP {name} already exists; remove or rename it first")
                        if not remove:
                            token = server.get("bearer_token_env_var")
                            if token and not os.environ.get(token):
                                raise ValueError(f"required bearer token environment variable is unset: {token}")
                            commands = expand(mcp_commands(host, name, server), REPO, root)
                            server = expand(server, REPO, root)
                            if server["type"] == "stdio" and shutil.which(server["command"], path=server.get("env", {}).get("PATH")) is None:
                                raise ValueError(f"MCP runtime executable unavailable: {server['command']}")
                        elif not exists:
                            commands = []
                jobs.append((kind, host, name, root, server, commands))
    install_skills.REPO = REPO
    if args.skill and not remove:
        install_skills.skill_dependencies(set(args.skill), install_skills.repo_skills())
    status = 0
    if args.skill:
        if remove:
            status = install_skills.cmd_unlink(args.host, args.skill, args.dry_run)
        else:
            status = install_skills.cmd_link(args.host, set(args.skill), args.prune, args.dry_run)
    for kind, host, name, root, server, commands in jobs:
        if kind == "skill":
            continue
        if args.dry_run:
            print(f"would {args.command}: {kind}:{name} -> {host} (native user configuration; source {root})")
        elif kind == "mcp" and host == "omp":
            write_omp_mcp(name, server, remove)
        else:
            run_commands(commands)
    return status


def sync_command(argv):
    if argv[0] == "import" or any(flag in argv for flag in ("--help", "-h")):
        return sync_upstream.main(argv)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--kind", choices=[*sync_upstream.COMPONENTS, "all"])
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--component", "--skill", action="append", default=[])
    options, remaining = parser.parse_known_args(argv[1:])
    if options.kind not in (None, "all") or (options.component and options.kind is None):
        return sync_upstream.main(argv)
    data = catalog(options.repo)
    selected = set(options.component)
    candidates = {kind: [entry["name"] for entry in data.get(key, [])
                         if entry.get("upstream") and (not selected or entry["name"] in selected)]
                  for kind, (key, _) in sync_upstream.COMPONENTS.items()}
    missing = selected - {name for names in candidates.values() for name in names}
    if missing:
        raise ValueError(f"unknown or untracked component: {', '.join(sorted(missing))}")
    codes = []
    for kind, names in candidates.items():
        if not names:
            continue
        command = [argv[0], *remaining, "--repo", str(options.repo), "--kind", kind]
        for name in names:
            command += ["--component", name]
        codes.append(sync_upstream.main(command))
    return max(codes, default=0)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in {"import", "check", "update"}:
        try:
            return sync_command(argv)
        except (ValueError, OSError, KeyError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["list", "hosts", "status", "install", "uninstall", "import", "check", "update"])
    parser.add_argument("--host", action="append", default=[])
    for kind in ("skill", "mcp", "plugin"):
        parser.add_argument(f"--{kind}", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prune", action="store_true", help="replace foreign skill symlinks; never replace real directories")
    args = parser.parse_args(argv)
    try:
        if args.command == "hosts":
            for host, path in install_skills.HOSTS.items():
                plugins = "native manifest required" if host in MCP_HOSTS else "unavailable"
                verified = " (runtime discovery unverified)" if host in {"dsh", "zcode", "cow"} else ""
                print(f"{host}: skills={install_skills.host_paths([host])[host]}{verified}; MCP={'yes' if host in MCP_HOSTS else 'unavailable'}; plugins={plugins}")
            return 0
        if args.command == "list":
            data = catalog(REPO)
            for kind, (key, _) in sync_upstream.COMPONENTS.items():
                for entry in data.get(key, []):
                    upstream = entry.get("upstream", {})
                    origin = upstream.get("repo") or upstream.get("package") or "self-developed/adapted"
                    pin = upstream.get("ref") or upstream.get("version") or ""
                    print(f"{kind}:{entry['name']}  {origin} {pin}")
            return 0
        if args.command == "status":
            if args.mcp or args.plugin:
                raise ValueError("status checks Skill links; inspect MCP/plugins with the host's native get/list command")
            install_skills.REPO = REPO
            return install_skills.cmd_status(args.host, set(args.skill))
        return install(args)
    except (ValueError, RuntimeError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
