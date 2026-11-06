"""Private settings and the real PlatformIO pre-build script, without hardware."""

import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from private_config import load_private_config

SCRIPT = Path(__file__).resolve().parents[1] / "firmware/scripts/load_secrets.py"


class PrivateConfigTests(unittest.TestCase):
    def test_file_quotes_comments_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('# private\nBADGE_ADMIN_KEY="test-key"\nBADGE_FINAL_FLAG=\'test-flag\'\n')
            values = load_private_config(path, {"BADGE_ADMIN_KEY": "environment-key"})
            self.assertEqual(values["BADGE_ADMIN_KEY"], "environment-key")
            self.assertEqual(values["BADGE_FINAL_FLAG"], "test-flag")
            self.assertEqual(load_private_config(path.with_name("missing"), {}), {})

    def test_invalid_settings_do_not_echo_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            for line in ['BADGE_ADMIN_KEY="private-test-value',
                         'BADGE_ADMIN_KEY="private-test-value\\n"',
                         'private-test-value']:
                path.write_text(line)
                with self.assertRaises(ValueError) as raised:
                    load_private_config(path, {})
                self.assertNotIn("private-test-value", str(raised.exception))

    def test_build_requires_secrets_and_only_exposes_an_include_path(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)

            class BuildEnv:
                appended = {}

                def subst(self, name):
                    return str(SCRIPT.parents[1] if name == "$PROJECT_DIR" else build)

                def Append(self, **values):
                    self.appended.update(values)

            env = BuildEnv()

            def run(settings):
                with patch("private_config.load_private_config", return_value=settings):
                    runpy.run_path(str(SCRIPT), init_globals={"env": env, "Import": lambda _: None})

            for settings in [{}, {"BADGE_ADMIN_KEY": "short"},
                             {"BADGE_ADMIN_KEY": "K" * 32, "BADGE_FINAL_FLAG": "invalid"}]:
                with self.assertRaises(SystemExit):
                    run(settings)
            self.assertFalse((build / "badge_secrets.h").exists())
            settings = {"BADGE_ADMIN_KEY": "K" * 32, "BADGE_FINAL_FLAG": "MSGCTF{TEST_ONLY}"}
            run(settings)
            header = (build / "badge_secrets.h").read_text()
            self.assertIn('#define BADGE_ADMIN_KEY "' + "K" * 32 + '"', header)
            self.assertIn('#define BADGE_FINAL_FLAG "MSGCTF{TEST_ONLY}"', header)
            self.assertEqual(env.appended, {"CPPPATH": [str(build)]})
            settings["BADGE_FINAL_FLAG"] = "MSGCTF{SECOND_TEST_ONLY}"
            run(settings)
            self.assertIn("SECOND_TEST_ONLY", (build / "badge_secrets.h").read_text())


if __name__ == "__main__":
    unittest.main()
