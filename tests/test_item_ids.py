"""`item_ids.txt` is the file mom edits by hand, so it has to survive what Notepad
and copy-paste do to it. Every case here is a shape that either crashed the run or
silently changed the output."""

import os
import tempfile
import unittest

from .harness import extractor

read_item_ids = extractor.read_item_ids


def write(text, encoding='utf-8'):
    fd, path = tempfile.mkstemp(suffix='.txt')
    os.close(fd)
    # newline='' so the CRLF case stays a CRLF case on Windows too
    with open(path, 'w', encoding=encoding, newline='') as f:
        f.write(text)
    return path


class ReadItemIdsTest(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def read(self, text, encoding='utf-8'):
        path = write(text, encoding)
        self.paths.append(path)
        return read_item_ids(path)

    def test_plain_file(self):
        self.assertEqual(self.read('70093\n19721\n'), [70093, 19721])

    def test_utf8_bom(self):
        # Notepad on Windows writes a BOM. This used to raise a bare ValueError.
        self.assertEqual(self.read('70093\n19721\n', encoding='utf-8-sig'), [70093, 19721])

    def test_blank_lines_and_whitespace(self):
        self.assertEqual(self.read('\n70093\n\n  19721  \n\n'), [70093, 19721])

    def test_comments(self):
        self.assertEqual(self.read('# baubles\n70093\n19721  # ecto\n'), [70093, 19721])

    def test_duplicates_dropped_order_kept(self):
        # The character loop walks this list directly, so a pasted duplicate used to
        # double that id's rows on every character.
        self.assertEqual(self.read('70093\n19721\n70093\n46653\n19721\n'),
                         [70093, 19721, 46653])

    def test_junk_line_is_skipped_not_fatal(self):
        # A report plus a warning beats a traceback and no report.
        self.assertEqual(self.read('70093\nShiny Bauble\n19721\n'), [70093, 19721])

    def test_no_trailing_newline(self):
        self.assertEqual(self.read('70093'), [70093])

    def test_empty_file(self):
        self.assertEqual(self.read(''), [])

    def test_crlf(self):
        self.assertEqual(self.read('70093\r\n19721\r\n'), [70093, 19721])


if __name__ == '__main__':
    unittest.main(verbosity=2)
