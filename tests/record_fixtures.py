"""Re-record the public API fixtures the tests run against.

Only the three unauthenticated endpoints are recorded. Authenticated responses
(account, characters, bank, materials, wallet) are hand-written in
`tests/fakeclient.py` instead - a recording of those would carry mom's account
name, character names and inventory into git.

Fixtures exist so the fake client cannot silently disagree with the real API
about response shape. Re-run after an API change, then read the diff:

    python tests/record_fixtures.py
"""

import json
import os
import urllib.request

BASE = 'https://api.guildwars2.com/v2'
HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, 'fixtures')

# One id per interesting shape, so the value rungs can be exercised against real data:
#   70093 Shiny Bauble            soulbound, vendor_value > 0  -> Vendor rung
#   19721 Glob of Ectoplasm       tradable                     -> TP rung
#   46653 Mini Princess Miya      NoSell but vendor_value > 0  -> no value (the NoSell trap)
#       4 Assassin Transform …    NoSell, vendor_value 0       -> no value; id collides with Gem
#      61 Rampager's Spineguard   id collides with Research Note
#   30689 Eternity                tradable *and* NoSell -> a bound copy has no value
#                                 at all; also carries a fat `details` blob nothing reads
ITEM_IDS = [70093, 19721, 46653, 4, 61, 30689]

# 1 Coin, 2 Karma, 4 Gem, 61 Research Note. 4 and 61 collide with item ids above.
CURRENCY_IDS = [1, 2, 4, 61]


def fetch(path):
    with urllib.request.urlopen(f'{BASE}/{path}') as r:
        return r.status, json.load(r)


def write(name, payload):
    path = os.path.join(FIXTURES, name)
    with open(path, 'w') as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write('\n')
    print(f'wrote {name} ({len(payload)} entries)')


def main():
    ids = ','.join(str(i) for i in ITEM_IDS)
    _, items = fetch(f'items?ids={ids}')
    write('items.json', items)

    # Untradable ids are dropped from the reply rather than zeroed, so this fixture
    # is deliberately shorter than ITEM_IDS - that absence is the tradability signal.
    status, prices = fetch(f'commerce/prices?ids={ids}')
    print(f'commerce/prices returned HTTP {status} with {len(prices)} of {len(ITEM_IDS)} ids')
    write('prices.json', prices)

    cids = ','.join(str(i) for i in CURRENCY_IDS)
    _, currencies = fetch(f'currencies?ids={cids}')
    write('currencies.json', currencies)


if __name__ == '__main__':
    main()
