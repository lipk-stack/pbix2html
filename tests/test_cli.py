import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from pbix2html.cli import main

from tests.helpers import build_pbix


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def write_sample(self, name: str = "sample.pbix") -> Path:
        path = self.tmp / name
        path.write_bytes(build_pbix().getvalue())
        return path

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_converts_to_default_output_path(self):
        sample = self.write_sample()
        code, out, err = self.run_cli(str(sample))
        self.assertEqual(code, 0, err)
        output = sample.with_suffix(".html")
        self.assertTrue(output.is_file())
        self.assertIn("<!DOCTYPE html>", output.read_text(encoding="utf-8"))
        self.assertIn("1 pages", out)

    def test_explicit_output_path(self):
        sample = self.write_sample()
        target = self.tmp / "out" "put.html"
        code, _, err = self.run_cli(str(sample), "-o", str(target))
        self.assertEqual(code, 0, err)
        self.assertTrue(target.is_file())

    def test_missing_file_returns_2(self):
        code, _, err = self.run_cli(str(self.tmp / "nope.pbix"))
        self.assertEqual(code, 2)
        self.assertIn("file not found", err)

    def test_invalid_file_returns_1(self):
        bad = self.tmp / "bad.pbix"
        bad.write_bytes(b"not a zip")
        code, _, err = self.run_cli(str(bad))
        self.assertEqual(code, 1)
        self.assertIn("not a readable PBIX archive", err)


if __name__ == "__main__":
    unittest.main()
