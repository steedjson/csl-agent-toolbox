"""Regression checks for skill validation under the skills/ namespace."""
import json
from pathlib import Path
import tempfile
import unittest

import validate_repo


class SkillLayoutTests(unittest.TestCase):
    def test_registered_skill_is_resolved_under_skills(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            skill = repo / "skills/demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo\n---\n")
            (repo / "skills.json").write_text(json.dumps({
                "skills": [{"name": "demo", "files": ["SKILL.md"]}]
            }))
            self.assertEqual(validate_repo.check_skills(repo), [])

    def test_contract_failure_under_skills_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            scripts = repo / "skills/demo/scripts"
            scripts.mkdir(parents=True)
            (scripts / "validate_contract.py").write_text(
                "print('broken contract')\nraise SystemExit(1)\n"
            )
            errors = validate_repo.check_skill_contracts(repo)
            self.assertEqual(len(errors), 1)
            self.assertIn("skills/demo/scripts/validate_contract.py", errors[0])
            self.assertIn("broken contract", errors[0])


if __name__ == "__main__":
    unittest.main()
