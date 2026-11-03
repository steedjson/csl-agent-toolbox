"""skills/html-design-draft/scripts/check_design.py 的定向测试。"""
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "html-design-draft" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from check_design import check_draft  # noqa: E402

GOOD_BOARD = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>春季菜单 · 海报</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC&display=swap" rel="stylesheet">
<style>
  .board { background: #FAF6EF url(../assets/bg.svg) no-repeat; }
</style>
</head>
<body>
<div class="board">
  <h1>春季菜单</h1>
  <img src="../assets/soup.jpg" alt="豌豆汤">
</div>
</body>
</html>
"""

GOOD_INDEX = """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>设计稿</title></head>
<body>
<a href="boards/poster.html">poster</a>
<iframe src="boards/poster.html"></iframe>
</body>
</html>
"""


def build_draft(tmp, board=GOOD_BOARD, index=GOOD_INDEX, with_assets=True, boards=None):
    root = Path(tmp)
    (root / "boards").mkdir(parents=True, exist_ok=True)
    if with_assets:
        (root / "assets").mkdir(exist_ok=True)
        (root / "assets" / "soup.jpg").write_bytes(b"\xff\xd8fake")
        (root / "assets" / "bg.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    if boards:
        for name, body in boards.items():
            (root / "boards" / name).write_text(body, encoding="utf-8")
    else:
        (root / "boards" / "poster.html").write_text(board, encoding="utf-8")
    if index is not None:
        (root / "index.html").write_text(index, encoding="utf-8")
    return root


class CheckDesignTest(unittest.TestCase):
    def test_good_draft_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, warnings = check_draft(build_draft(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_missing_index_and_boards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "boards").mkdir()
            errors, _ = check_draft(root)
            self.assertTrue(any("index.html" in e for e in errors))
            self.assertTrue(any("boards" in e for e in errors))

    def test_forbidden_script_tag(self):
        bad = GOOD_BOARD.replace("</body>", "<script>alert(1)</script></body>")
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("禁用标签 <script>" in e for e in errors))

    def test_iframe_allowed_only_in_index(self):
        bad = GOOD_BOARD.replace("</body>", "<iframe src='x.html'></iframe></body>")
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("<iframe>" in e for e in errors))
        with tempfile.TemporaryDirectory() as tmp:  # index 里 iframe 豁免
            errors, _ = check_draft(build_draft(tmp))
            self.assertFalse(any("<iframe>" in e for e in errors))

    def test_data_uri_rejected(self):
        bad = GOOD_BOARD.replace('src="../assets/soup.jpg"', 'src="data:image/png;base64,xxx"')
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("data:" in e for e in errors))

    def test_external_cdn_rejected_but_google_fonts_allowed(self):
        bad = GOOD_BOARD.replace(
            '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC&display=swap" rel="stylesheet">',
            '<link href="https://cdn.example.com/font.css" rel="stylesheet">')
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("cdn.example.com" in e for e in errors))
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp))
            self.assertFalse(any("fonts.googleapis" in e for e in errors))

    def test_missing_local_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, with_assets=False))
            self.assertTrue(any("本地资源不存在" in e for e in errors))

    def test_empty_title_and_missing_doctype(self):
        bad = GOOD_BOARD.replace("<!doctype html>\n", "").replace("春季菜单 · 海报", "")
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("doctype" in e for e in errors))
            self.assertTrue(any("<title> 为空" in e for e in errors))

    def test_absolute_path_rejected(self):
        bad = GOOD_BOARD.replace('src="../assets/soup.jpg"', 'src="/assets/soup.jpg"')
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("绝对路径" in e for e in errors))

    def test_img_without_alt_is_warning_not_error(self):
        bad = GOOD_BOARD.replace(' alt="豌豆汤"', "")
        with tempfile.TemporaryDirectory() as tmp:
            errors, warnings = check_draft(build_draft(tmp, board=bad))
            self.assertEqual(errors, [])
            self.assertTrue(any("缺 alt" in w for w in warnings))

    def test_inline_style_url_refs_checked(self):
        bad = GOOD_BOARD.replace('class="board"', 'class="board" style="background:url(/assets/bg.png)"')
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_draft(build_draft(tmp, board=bad))
            self.assertTrue(any("绝对路径" in e and "url()" in e for e in errors))
        with tempfile.TemporaryDirectory() as tmp:  # <style> 块内同样检查
            errors, _ = check_draft(build_draft(tmp))
            self.assertFalse(any("url()" in e for e in errors))

    def test_index_not_referencing_board_is_warning(self):
        index = GOOD_INDEX.replace('href="boards/poster.html"', 'href="#"').replace('src="boards/poster.html"', 'src="#"')
        with tempfile.TemporaryDirectory() as tmp:
            errors, warnings = check_draft(build_draft(tmp, index=index))
            self.assertEqual(errors, [])
            self.assertTrue(any("未引用画板" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
