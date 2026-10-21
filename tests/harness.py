"""Shared test rig: the extractor module, the recorded fixtures, and a fake client.

Every test module imports from here so one set of API payloads backs the whole
suite. Nothing in the suite touches the network or an API key.

Split by design:
  * Public endpoints (items, prices, currencies) are *recorded* - real shapes, kept
    honest by `record_fixtures.py`. If the API changes, the recording changes and the
    diff is visible.
  * Authenticated endpoints (account, characters, bank, materials, shared, wallet) are
    *hand-written* below. A recording of those would put mom's account name, character
    names and inventory into git.
"""

import copy
import csv
import importlib.util
import json
import os
import sys
import tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, 'fixtures')


def _load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return {entry['id']: entry for entry in json.load(f)}


# Recorded. Keyed by id for lookup; the fake client hands back list slices.
ITEMS = _load_fixture('items.json')
PRICES = _load_fixture('prices.json')
CURRENCIES = _load_fixture('currencies.json')

# The ids these fixtures cover, and why each one is here.
SHINY = 70093      # the thing mom actually hunts: soulbound, vendor_value 3000
ECTO = 19721       # tradable, unbound -> the TP rung
MINI = 46653       # NoSell but advertises vendor_value 50 -> the NoSell trap
TRANSFORM = 4      # vendor_value 0 + NoSell; id collides with the Gem currency
SPINEGUARD = 61    # id collides with the Research Note currency
ETERNITY = 30689   # tradable *and* NoSell -> bound copies fall all the way through

SHINY_NAME = 'Shiny Bauble'

# Hand-written account payloads. Decoys sit in every section so a filter leak from any
# one source fails its own assertion, and the None/empty slots are the shapes that have
# crashed the script before.
ACCOUNT_NAME = 'tester.1234'

SHARED = [None, {'id': SHINY, 'count': 1}, {'id': ECTO, 'count': 2}]
MATERIALS = [{'id': ECTO, 'count': 250}, {'id': TRANSFORM, 'count': 1}]
BANK = [{'id': SPINEGUARD, 'count': 1}, None, {'id': SHINY, 'count': 3}]

CHARACTERS = {
    'Hoarder': {'bags': [
        {'inventory': [{'id': SHINY, 'count': 5, 'binding': None}, None,
                       {'id': TRANSFORM, 'count': 1, 'binding': 'Account'}]},
        None,                   # an empty bag slot
        {'inventory': []},      # a bag holding nothing
    ]},
    # Owns no baubles at all - the filtered branch still emits a zero row for her.
    'Decoychar': {'bags': [
        {'inventory': [{'id': ECTO, 'count': 7, 'binding': None}]},
    ]},
}

WALLET = [{'id': 1, 'value': 123456}, {'id': 2, 'value': 98765},
          {'id': 4, 'value': 800}, {'id': 61, 'value': 42}]


class _Endpoint:
    def __init__(self, fn):
        self._fn = fn

    def get(self, *args, **kwargs):
        return self._fn(*args, **kwargs)


class FakeClient:
    """Answers exactly the calls GW2-extractor.py makes, from the fixtures above.

    Every payload is deep-copied on the way out, so a test that mutates what it gets
    back cannot poison the next one."""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.account = _Endpoint(lambda: {'name': ACCOUNT_NAME})
        self.accountinventory = _Endpoint(lambda: copy.deepcopy(SHARED))
        self.accountmaterials = _Endpoint(lambda: copy.deepcopy(MATERIALS))
        self.accountbank = _Endpoint(lambda: copy.deepcopy(BANK))
        self.accountwallet = _Endpoint(lambda: copy.deepcopy(WALLET))
        self.characters = _Endpoint(lambda: list(CHARACTERS))
        self.charactersinventory = _Endpoint(lambda name: copy.deepcopy(CHARACTERS[name]))
        self.items = _Endpoint(self._items)
        self.commerceprices = _Endpoint(self._prices)
        self.currencies = _Endpoint(self._currencies)

    @staticmethod
    def _items(ids=None):
        return [copy.deepcopy(ITEMS[i]) for i in ids if i in ITEMS]

    @staticmethod
    def _prices(ids=None):
        # Untradable ids are absent from the reply rather than zeroed - that absence is
        # how the script knows an item cannot be listed. Recorded live as HTTP 206.
        return [copy.deepcopy(PRICES[i]) for i in ids if i in PRICES]

    @staticmethod
    def _currencies(ids=None):
        if ids is None:
            return list(CURRENCIES)
        return [copy.deepcopy(CURRENCIES[i]) for i in ids if i in CURRENCIES]


def load_extractor():
    """Import GW2-extractor.py by path - the hyphen makes it unimportable by name."""
    path = os.path.join(REPO, 'GW2-extractor.py')
    spec = importlib.util.spec_from_file_location('gw2_extractor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extractor = load_extractor()


def items_dict(ids=None):
    """The items dict build_rows expects, without going through the client."""
    if ids is None:
        return copy.deepcopy(ITEMS)
    return {i: copy.deepcopy(ITEMS[i]) for i in ids if i in ITEMS}


def prices_dict(ids=None):
    if ids is None:
        return copy.deepcopy(PRICES)
    return {i: copy.deepcopy(PRICES[i]) for i in ids if i in PRICES}


def run_extractor(extra_args):
    """Run main() end to end against the fake client; return the CSV rows as dicts.

    `--api-keys` gets a literal string rather than a path, so no key file is read."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'out.csv')
        argv = ['GW2-extractor.py', '--api-keys', 'FAKE-KEY-NOT-A-FILE'] + \
               list(extra_args) + ['--output', out]
        with mock.patch.object(extractor, 'GuildWars2Client', FakeClient), \
             mock.patch.object(sys, 'argv', argv):
            extractor.main()
        with open(out, newline='') as f:
            reader = csv.DictReader(f)
            return reader.fieldnames, list(reader)
