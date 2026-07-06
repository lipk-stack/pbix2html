import io
import unittest
import zipfile
from unittest.mock import patch

from pbix2html.reader import PbixError, read_pbix
from tests.helpers import build_pbix


class ReaderLimitTests(unittest.TestCase):
    def test_rejects_layout_member_over_limit(self):
        pbix = build_pbix()
        with patch("pbix2html.reader.MAX_LAYOUT_BYTES", 32):
            with self.assertRaises(PbixError):
                read_pbix(pbix)

    def test_rejects_archive_with_too_many_members(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("Report/Layout", b"{}")
            archive.writestr("extra.txt", b"x")
        buffer.seek(0)
        with patch("pbix2html.reader.MAX_ARCHIVE_MEMBERS", 1):
            with self.assertRaises(PbixError):
                read_pbix(buffer)


if __name__ == "__main__":
    unittest.main()
