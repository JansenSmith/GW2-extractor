"""Asking for one item must return only that item.

Mom's complaint: a report for Shiny Baubles (70093) comes back full of rows she
never asked for. The fixtures here deliberately include every shape that could
leak - decoy items in every storage section, empty and None bag slots, and
wallet currencies whose ids (4, 61) collide with real item ids - so a leak from
any one source fails a named assertion.

Runs fully offline: GuildWars2Client is replaced with a fake, and the API key is
passed as a literal string so no real key file is read.

    python test_baubles_only.py
"""

import csv
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

SHINY = 70093
SHINY_NAME = 'Shiny Bauble'

# Decoy items. 4 and 61 are the ids that also exist as currencies.
ITEMS = {
    SHINY: {'id': SHINY, 'name': SHINY_NAME, 'vendor_value': 8, 'flags': [],
            'description': 'A shiny bauble.'},
    4:     {'id': 4, 'name': 'Assassin Transform Weapon', 'vendor_value': 0,
            'flags': ['NoSell'], 'description': ''},
    61:    {'id': 61, 'name': "Rampager's Spineguard of Coral", 'vendor_value': 11,
            'flags': [], 'description': ''},
    18729: {'id': 18729, 'name': 'Bolt of Linen', 'vendor_value': 16, 'flags': [],
            'description': ''},
}

PRICES = {
    SHINY: {'id': SHINY, 'sells': {'unit_price': 1000}},
    18729: {'id': 18729, 'sells': {'unit_price': 500}},
}

# Currency ids 4 and 61 collide with item ids 4 and 61 above.
CURRENCIES = {
    1:  {'id': 1, 'name': 'Coin', 'description': 'The currency of Tyria.'},
    4:  {'id': 4, 'name': 'Gem', 'description': 'Gem Store currency.'},
    61: {'id': 61, 'name': 'Research Note', 'description': 'Crafting currency.'},
}

SHARED = [None, {'id': SHINY, 'count': 1}, {'id': 18729, 'count': 2}]
MATERIALS = [{'id': 18729, 'count': 250}, {'id': 4, 'count': 1}]
BANK = [{'id': 61, 'count': 1}, None, {'id': SHINY, 'count': 3}]

CHARACTERS = {
    'Hoarder': {'bags': [
        {'inventory': [{'id': SHINY, 'count': 5, 'binding': None}, None,
                       {'id': 4, 'count': 1, 'binding': 'Account'}]},
        None,
        {'inventory': []},
    ]},
    # Owns no baubles at all - the filtered branch still emits a zero row for her.
    'Decoychar': {'bags': [
        {'inventory': [{'id': 18729, 'count': 7, 'binding': None}]},
    ]},
}

WALLET = [{'id': 1, 'value': 123456}, {'id': 4, 'value': 800}, {'id': 61, 'value': 42}]


class _Endpoint:
    def __init__(self, fn):
        self._fn = fn

    def get(self, *args, **kwargs):
        return self._fn(*args, **kwargs)


class FakeClient:
    """Answers exactly the calls GW2-extractor.py makes, from the fixtures above."""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.account = _Endpoint(lambda: {'name': 'jazz.1234'})
        self.accountinventory = _Endpoint(lambda: SHARED)
        self.accountmaterials = _Endpoint(lambda: MATERIALS)
        self.accountbank = _Endpoint(lambda: BANK)
        self.accountwallet = _Endpoint(lambda: WALLET)
        self.characters = _Endpoint(lambda: list(CHARACTERS))
        self.charactersinventory = _Endpoint(lambda name: CHARACTERS[name])
        self.items = _Endpoint(self._items)
        self.commerceprices = _Endpoint(self._prices)
        self.currencies = _Endpoint(self._currencies)

    @staticmethod
    def _items(ids=None):
        return [ITEMS[i] for i in ids if i in ITEMS]

    @staticmethod
    def _prices(ids=None):
        return [PRICES[i] for i in ids if i in PRICES]

    @staticmethod
    def _currencies(ids=None):
        if ids is None:
            return list(CURRENCIES)
        return [CURRENCIES[i] for i in ids if i in CURRENCIES]


def load_extractor():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GW2-extractor.py')
    spec = importlib.util.spec_from_file_location('gw2_extractor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_extractor(extra_args):
    """Run main() against the fake client and return the CSV rows as dicts."""
    module = load_extractor()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'out.csv')
        argv = ['GW2-extractor.py', '--api-keys', 'FAKE-KEY-NOT-A-FILE'] + extra_args + \
               ['--output', out]
        with mock.patch.object(module, 'GuildWars2Client', FakeClient), \
             mock.patch.object(sys, 'argv', argv):
            module.main()
        with open(out, newline='') as f:
            return list(csv.DictReader(f))


class BaublesOnlyTest(unittest.TestCase):
    """The exact shape of mom's report: one item id, every storage section on."""

    @classmethod
    def setUpClass(cls):
        cls.rows = run_extractor([
            '--item-ids', str(SHINY),
            '--get-shared', '--get-materials', '--get-bank', '--get-wallet',
        ])

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
        # shared (1) + bank (1) + one row per character (2). Materials hold no
        # baubles, so they contribute nothing. Decoychar's row is a zero row.
        self.assertEqual(len(self.rows), 4, [r['Character Name'] for r in self.rows])

    def test_the_bauble_rows_survived(self):
        amounts = {r['Character Name']: r['Amount'] for r in self.rows}
        self.assertEqual(amounts['jazz.1234.shared'], '1')
        self.assertEqual(amounts['jazz.1234.bank'], '3')
        self.assertEqual(amounts['Hoarder'], '5')
        self.assertEqual(amounts['Decoychar'], '0')


class UnfilteredStillHasWalletTest(unittest.TestCase):
    """The fix must not touch the full dump - there --get-wallet is the whole point."""

    @classmethod
    def setUpClass(cls):
        cls.rows = run_extractor([
            '--get-unfiltered',
            '--get-shared', '--get-materials', '--get-bank', '--get-wallet',
        ])

    def test_wallet_rows_present(self):
        wallet = [r for r in self.rows if r['Character Name'].endswith('.wallet')]
        self.assertEqual(len(wallet), len(CURRENCIES))

    def test_decoy_items_present(self):
        ids = {r['Item ID'] for r in self.rows}
        self.assertIn('18729', ids)


if __name__ == '__main__':
    unittest.main(verbosity=2)
