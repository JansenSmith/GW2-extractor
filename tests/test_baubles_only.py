"""End to end: asking for one item must return only that item.

Mom's complaint, in test form - a report for Shiny Baubles came back full of rows she
never asked for. This runs `main()` whole, through argument parsing and CSV writing,
so it covers the plumbing the unit tests skip: which flags reach which section, and
what the file on disk actually looks like.

The per-section filtering and the value rungs are pinned in `test_build_rows.py`.
"""

import contextlib
import io
import os
import tempfile
import unittest

from .harness import ACCOUNT_NAME, CURRENCIES, ECTO, SHINY, SHINY_NAME, extractor, run_extractor


class BaublesOnlyTest(unittest.TestCase):
    """The exact shape of mom's run: one item id, every storage section switched on."""

    @classmethod
    def setUpClass(cls):
        cls.fieldnames, cls.rows = run_extractor([
            '--item-ids', str(SHINY),
            '--get-shared', '--get-materials', '--get-bank', '--get-wallet',
        ])

    def test_column_order(self):
        # Her sheet formulas point at positions, so this order is a contract.
        self.assertEqual(self.fieldnames, extractor.COLUMNS)

    def test_no_wallet_rows(self):
        wallet = [r for r in self.rows if r['Character Name'].endswith('.wallet')]
        self.assertEqual(wallet, [], 'wallet currencies leaked into a filtered report')

    def test_every_row_is_the_requested_id(self):
        stray = sorted({r['Item ID'] for r in self.rows} - {str(SHINY)})
        self.assertEqual(stray, [], f'unrequested item ids in output: {stray}')

    def test_every_row_is_named_shiny_bauble(self):
        stray = sorted({r['Item Name'] for r in self.rows} - {SHINY_NAME})
        self.assertEqual(stray, [], f'unrequested item names in output: {stray}')

    def test_row_count(self):
        # shared (1) + bank (1) + one row per character (2). Materials hold no baubles,
        # so they contribute nothing. Decoychar's row is a zero row.
        self.assertEqual(len(self.rows), 4, [r['Character Name'] for r in self.rows])

    def test_the_bauble_rows_survived(self):
        amounts = {r['Character Name']: r['Amount'] for r in self.rows}
        self.assertEqual(amounts[ACCOUNT_NAME + '.shared'], '1')
        self.assertEqual(amounts[ACCOUNT_NAME + '.bank'], '3')
        self.assertEqual(amounts['Hoarder'], '5')
        self.assertEqual(amounts['Decoychar'], '0')

    def test_value_column_is_filled(self):
        # Baubles are soulbound, so this is the vendor rung, not the trading post.
        for row in self.rows:
            self.assertEqual(row['Source'], 'Vendor')
            self.assertEqual(row['Value'], '0.3000')


class WalletFlagIsReportedTest(unittest.TestCase):
    """Dropping a flag the caller passed has to be said out loud, not done silently."""

    def test_note_names_the_flag_and_the_reason(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_extractor(['--item-ids', str(SHINY), '--get-wallet'])
        printed = buf.getvalue()
        self.assertIn('--get-wallet ignored', printed)
        self.assertIn('--item-ids', printed)


class ItemIdsFromFileTest(unittest.TestCase):
    """Mom passes a file, not ids on the command line. Same result, plus the tolerant
    parsing on the way in."""

    def test_file_with_bom_comments_and_duplicates(self):
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        try:
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write('# what I am hunting\n')
                f.write(f'{SHINY}\n\n{SHINY}\n')
            _, rows = run_extractor(['--item-ids', path, '--get-shared', '--get-bank'])
        finally:
            os.unlink(path)
        self.assertEqual({r['Item ID'] for r in rows}, {str(SHINY)})
        # The duplicate must not double the character rows.
        self.assertEqual(len(rows), 4)


class UnfilteredStillHasEverythingTest(unittest.TestCase):
    """The fix must not touch the full dump - there --get-wallet is the whole point."""

    @classmethod
    def setUpClass(cls):
        cls.fieldnames, cls.rows = run_extractor([
            '--get-unfiltered',
            '--get-shared', '--get-materials', '--get-bank', '--get-wallet',
        ])

    def test_wallet_rows_present_and_first(self):
        wallet = [r for r in self.rows if r['Character Name'].endswith('.wallet')]
        self.assertEqual(len(wallet), len(CURRENCIES))
        self.assertEqual([r['Character Name'] for r in self.rows[:len(CURRENCIES)]],
                         [ACCOUNT_NAME + '.wallet'] * len(CURRENCIES))

    def test_decoy_items_present(self):
        self.assertIn(str(ECTO), {r['Item ID'] for r in self.rows})


if __name__ == '__main__':
    unittest.main(verbosity=2)
