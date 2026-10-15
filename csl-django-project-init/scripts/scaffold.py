#!/usr/bin/env python3
"""确定性 Django 项目脚手架渲染器(csl-django-project-init 技能附属)。

将技能 templates/ 下的脱敏基线(wework/backend + stdkit v1.2.6 提炼)渲染到目标目录:
- 替换占位符 __CONF_PACKAGE__ / __TABLE_PREFIX__ / __PROJECT_NAME__ / __APP_NAME__ / __APP_CLASS__;
- conf_package/ 目录重命名为实际配置包名;
- --app NAME 可重复,按 app_skeleton/ 生成业务 app 骨架;
- stdkit/ 基架随模板逐字拷入项目根(不入库,已列 .gitignore),传递依赖已固化在 requirements 模板。

安全约束:目标目录必须不存在或为空;--force 允许非空目标但绝不覆盖已有文件。
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

RENDER_TOKENS = ("__CONF_PACKAGE__", "__TABLE_PREFIX__", "__PROJECT_NAME__", "__APP_NAME__", "__APP_CLASS__")

APP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def render_text(content: str, ctx: dict) -> str:
    for token, value in ctx.items():
        content = content.replace(token, value)
    return content


def copy_tree_rendered(src: Path, dst: Path, ctx: dict, written: list, executable_names: set) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        rel_rendered = render_text(str(rel), ctx)
        target = dst / rel_rendered
        if target.exists():
            print(f"  跳过(已存在): {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = path.read_text(encoding="utf-8")
        target.write_text(render_text(content, ctx), encoding="utf-8")
        if path.name in executable_names:
            target.chmod(0o755)
        written.append(target)


def app_class_name(app_name: str) -> str:
    return "".join(part.capitalize() for part in app_name.split("_")) + "Config"


def copy_stdkit_baseline(target: Path, written: list) -> None:
    """stdkit 基架从模板逐字拷入项目根(不做占位符替换,保持源码原样)。"""
    stdkit_dir = target / "stdkit"
    stdkit_dir.mkdir(parents=True, exist_ok=True)
    source = TEMPLATES / "stdkit"
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(source)
        dst = stdkit_dir / rel
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        written.append(dst)


def check_no_residue(target: Path) -> list:
    residue = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.suffix in (".py", ".md", ".ini", ".toml", ".txt", ".cfg", ".yaml", ".yml"):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for token in RENDER_TOKENS:
                if token in content:
                    residue.append(f"{path}: {token}")
    return residue


def main() -> int:
    parser = argparse.ArgumentParser(description="按 wework/backend 基线渲染 Django 项目骨架")
    parser.add_argument("target", help="目标项目目录(必须不存在或为空)")
    parser.add_argument("--conf", default="backend", help="Django 配置包名(默认 backend)")
    parser.add_argument("--project", default=None, help="项目名(默认取 target 目录名)")
    parser.add_argument("--prefix", default=None, help="数据库表名前缀(默认 <conf>_)")
    parser.add_argument("--app", action="append", default=[], metavar="NAME", help="业务 app 名,可重复")
    parser.add_argument("--no-stdkit", action="store_true", help="不拷入 stdkit/ 基架(默认拷入)")
    parser.add_argument("--force", action="store_true", help="允许非空目标(仍绝不覆盖已有文件)")
    args = parser.parse_args()

    if not IDENTIFIER_RE.match(args.conf):
        print(f"配置包名不合法: {args.conf}(需为合法 Python 包名)", file=sys.stderr)
        return 2
    project = args.project or Path(args.target).resolve().name
    if not project:
        print("无法从 target 推断项目名,请用 --project 指定", file=sys.stderr)
        return 2
    prefix = args.prefix if args.prefix is not None else f"{args.conf}_"
    for app in args.app:
        if not APP_NAME_RE.match(app):
            print(f"业务 app 名不合法: {app}(小写字母/数字/下划线,字母开头)", file=sys.stderr)
            return 2

    target = Path(args.target).resolve()
    if target.exists():
        if not target.is_dir():
            print(f"目标不是目录: {target}", file=sys.stderr)
            return 2
        if any(target.iterdir()) and not args.force:
            print(f"目标目录非空: {target}(确认后可用 --force,已有文件不会被覆盖)", file=sys.stderr)
            return 2

    ctx = {
        "__CONF_PACKAGE__": args.conf,
        "__TABLE_PREFIX__": prefix,
        "__PROJECT_NAME__": project,
        "__APP_NAME__": "__APP_NAME__",  # app 骨架渲染时单独覆盖
        "__APP_CLASS__": "__APP_CLASS__",
    }

    target.mkdir(parents=True, exist_ok=True)
    written = []

    # 根文件 + 配置包 + common + apps 基线(root 内含 scripts/,一并渲染)
    copy_tree_rendered(
        TEMPLATES / "root", target, ctx, written, {"manage.py", "compiler.py", "local_quality_gate.sh"}
    )
    copy_tree_rendered(TEMPLATES / "conf_package", target / args.conf, ctx, written, set())
    copy_tree_rendered(TEMPLATES / "common", target / "common", ctx, written, set())
    copy_tree_rendered(TEMPLATES / "apps", target / "apps", ctx, written, set())

    # 业务 app 骨架
    for app in args.app:
        app_ctx = dict(ctx)
        app_ctx["__APP_NAME__"] = app
        app_ctx["__APP_CLASS__"] = app_class_name(app)
        copy_tree_rendered(TEMPLATES / "app_skeleton", target / "apps" / app, app_ctx, written, set())

    # stdkit 基架(模板自带,逐字拷入;--no-stdkit 跳过)
    if args.no_stdkit:
        print("stdkit 基架未拷入(--no-stdkit);requirements.txt 末段的 stdkit 传递依赖需自行处理")
    else:
        copy_stdkit_baseline(target, written)
        print("stdkit/ 基架已拷入并随项目仓库分发(传递依赖见 requirements.txt 末段;pre-commit 已排除,保持字节稳定)")

    # 运行时空目录(git 不追踪空目录,放 .gitkeep)
    for empty_dir in ("logs", "media", "statics", "data", "tests"):
        keeper = target / empty_dir / ".gitkeep"
        if not keeper.exists():
            keeper.parent.mkdir(parents=True, exist_ok=True)
            keeper.write_text("", encoding="utf-8")
            written.append(keeper)

    residue = check_no_residue(target)
    if residue:
        print("渲染残留占位符(渲染缺陷,需修复 scaffold.py):", file=sys.stderr)
        for line in residue:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"已渲染 {len(written)} 个文件到 {target}")
    print("\n后续步骤:")
    print(f"  1. python3.12 -m venv {target}/.venv && {target}/.venv/bin/pip install -r {target}/requirements.txt")
    print(f"  2. cp {target}/{args.conf}/settings_local.example.py {target}/{args.conf}/settings_local.py 并按环境修改")
    print(f"  3. {target}/.venv/bin/python {target}/manage.py check")
    print(f"  4. make migrate && make dev(在 {target} 内)")
    print(f"  5. 建议安装 django-test-sandbox 技能获得完整 PG→SQLite 测试沙盒")
    return 0


if __name__ == "__main__":
    sys.exit(main())
