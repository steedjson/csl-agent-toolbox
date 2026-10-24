"""Regression checks for the vendored UI design token CLI."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "ui-design-system/scripts/design_token_generator.py"


class DesignTokenGeneratorTests(unittest.TestCase):
    def run_cli(self, style, output_format):
        return subprocess.check_output(
            [sys.executable, str(SCRIPT), "#0066CC", "--style", style, "--format", output_format],
            text=True,
        )

    def test_styles_and_output_formats(self):
        for style in ("modern", "classic", "playful"):
            with self.subTest(style=style):
                tokens = json.loads(self.run_cli(style, "json"))
                self.assertEqual(tokens["meta"]["style"], style)
                self.assertEqual(tokens["colors"]["primary"]["DEFAULT"], "#0066CC")
                self.assertEqual(tokens["typography"]["fontSize"]["base"], "16px")
                css = self.run_cli(style, "css")
                self.assertTrue(css.startswith(":root {\n"))
                self.assertIn("--colors-primary-DEFAULT: #0066CC;", css)
                scss = self.run_cli(style, "scss")
                self.assertIn("$colors-primary-DEFAULT: #0066CC;", scss)
                self.assertTrue(all(line.startswith("$") and line.endswith(";")
                                    for line in scss.splitlines()))
                css_values = dict(line.strip()[2:].split(": ", 1)
                                  for line in css.splitlines()[1:-1])
                scss_values = dict(line[1:].split(": ", 1) for line in scss.splitlines())
                self.assertEqual(scss_values, css_values)
                self.assertIn(f"Style: {style}", self.run_cli(style, "summary"))


if __name__ == "__main__":
    unittest.main()
