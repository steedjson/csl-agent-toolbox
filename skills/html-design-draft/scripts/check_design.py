#!/usr/bin/env python3
"""校验 html-design-draft 设计稿目录。

用法: python3 check_design.py <draft_dir>

只做确定性检查(自包含性、本地资源存在性、结构必备项、index 对应关系)；
美的问题(对比度、间距、字号档)不在此列,仍按 SKILL.md 踩坑规则人工过。

退出码: 有 ERROR 为 1,否则 0(WARN 不影响)。
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
FORBIDDEN_TAGS = {"script", "iframe", "object", "embed"}  # iframe 仅 index.html 豁免
URL_IN_CSS = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")


class BoardParser(HTMLParser):
    """收集结构必备项、违规引用与本地资源引用。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.doctype = False
        self.lang = None
        self.charset = False
        self.title_parts = []
        self._in_title = False
        self.style_chunks = []
        self._in_style = False
        self.problems = []  # (lineno, message) — 均为 error 级
        self.local_refs = []  # (lineno, relative_path)
        self.imgs_no_alt = 0

    # -- 结构与文本 ------------------------------------------------------
    def handle_decl(self, decl):
        if decl.lower() == "doctype html":
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        line, _ = self.getpos()
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta" and a.get("charset"):
            self.charset = True
        if tag == "title":
            self._in_title = True
        if tag == "style":
            self._in_style = True
        if tag == "img" and not a.get("alt"):
            self.imgs_no_alt += 1
        if tag in FORBIDDEN_TAGS:
            self.problems.append((line, f"禁用标签 <{tag}>"))
        for key in ("src", "href"):
            self._check_ref(line, key, (a.get(key) or "").strip())
        if a.get("style"):
            self._check_css_refs(line, a["style"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._in_style:
            self.style_chunks.append(data)

    # -- 引用分类 --------------------------------------------------------
    def _check_css_refs(self, line, css_text):
        """行内 style 属性与 <style> 块里的 url() 引用。"""
        for ref in URL_IN_CSS.findall(css_text):
            ref = ref.strip()
            if ref.startswith("data:"):
                self.problems.append((line, "CSS url() 使用 data: URI"))
            elif ref.startswith(("http://", "https://", "//")):
                host = ref.split("//", 1)[-1].split("/", 1)[0]
                if host not in ALLOWED_HOSTS:
                    self.problems.append((line, f"CSS url() 外链 {ref[:60]} 不在允许清单"))
            elif ref.startswith("/"):
                self.problems.append((line, f"CSS url() 绝对路径 {ref} 破坏可移植性"))
            else:
                self.local_refs.append((line, ref))

    def _check_ref(self, line, key, ref):
        if not ref or ref.startswith(("#", "mailto:")):
            return
        if ref.startswith("data:"):
            self.problems.append((line, f"{key} 使用 data: URI"))
        elif ref.startswith(("http://", "https://", "//")):
            host = ref.split("//", 1)[-1].split("/", 1)[0]
            if host not in ALLOWED_HOSTS:
                self.problems.append((line, f"外链 {ref[:60]} 不在允许清单(仅 Google Fonts)"))
        elif ref.startswith("/"):
            self.problems.append((line, f"绝对路径 {ref} 破坏可移植性"))
        else:
            self.local_refs.append((line, ref))


def check_html_file(path: Path, allow_iframe: bool = False):
    """校验单个 HTML。返回 (errors, warnings) — (lineno, message) 列表。"""
    parser = BoardParser()
    text = path.read_text(encoding="utf-8", errors="replace")
    parser.feed(text)
    parser.close()
    errors = [
        (line, msg) for line, msg in parser.problems
        if not (allow_iframe and msg == "禁用标签 <iframe>")
    ]
    warnings = []

    if not parser.doctype:
        errors.append((1, "缺 <!doctype html>"))
    if not parser.lang:
        errors.append((1, "<html> 缺 lang 属性"))
    if not parser.charset:
        errors.append((1, "缺 <meta charset>"))
    if not "".join(parser.title_parts).strip():
        errors.append((1, "<title> 为空"))

    for chunk in parser.style_chunks:
        parser._check_css_refs(1, chunk)

    for line, ref in parser.local_refs:
        target = (path.parent / ref.split("?")[0].split("#")[0]).resolve()
        if not target.exists():
            errors.append((line, f"本地资源不存在: {ref}"))

    if parser.imgs_no_alt:
        warnings.append((0, f"{parser.imgs_no_alt} 个 <img> 缺 alt"))
    return errors, warnings, text


def check_draft(draft: Path):
    """校验设计稿目录。返回 (errors, warnings),元素为 "file:line message"。"""
    out_errors, out_warnings = [], []

    def add(bucket, file, items):
        for line, msg in items:
            bucket.append(f"{file}:{line} {msg}")

    if not draft.is_dir():
        return [f"{draft}: 不是目录"], []
    index = draft / "index.html"
    boards_dir = draft / "boards"
    boards = sorted(boards_dir.glob("*.html")) if boards_dir.is_dir() else []
    if not index.exists():
        out_errors.append("index.html:1 缺失")
    if not boards:
        out_errors.append("boards/:1 没有画板文件")

    index_text = ""
    for f in [index, *boards]:
        if not f.exists():
            continue
        rel = f.relative_to(draft)
        errors, warnings, text = check_html_file(f, allow_iframe=(f == index))
        if f == index:
            index_text = text
        add(out_errors, rel, errors)
        add(out_warnings, rel, warnings)

    if index_text and boards:
        for b in boards:
            if b.name not in index_text:
                out_warnings.append(f"index.html:1 未引用画板 {b.name}")
    return out_errors, out_warnings


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    errors, warnings = check_draft(Path(argv[1]))
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print(f"共 {len(errors)} 个问题未通过。", file=sys.stderr)
        return 1
    print(f"OK: 0 errors, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
