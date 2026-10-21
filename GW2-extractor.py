import pandas as pd
from gw2api import GuildWars2Client
from requests.exceptions import HTTPError
import time
import argparse
import sys
import os

def display_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    try:
        with open(readme_path, 'r') as f:
            print(f.read())
    except FileNotFoundError:
        print("README.md not found. Please ensure README.md exists in the same directory.")
        print("\nThis script is designed to be called with arguments from other scripts.")
        print("Run with --help for argument details.")


TP_FEE_MULTIPLIER = 0.85  # 5% listing fee + 10% exchange fee, both taken out of the seller's cut
NO_VALUE_SOURCE = '-'


def read_api_keys(path):
    """Read one key per line, ignoring blanks, comments, and anything after a comma.
    A trailing label like 'KEY,jazz' is a note to self, not part of the key - sending it
    whole is what caused a 401 in June."""
    keys = []
    with open(path, 'r') as opened_api_file:
        for line in opened_api_file:
            line = line.split('#', 1)[0]
            key = line.split(',', 1)[0].strip()
            if key:
                keys.append(key)
    return keys


def batch_get_items(gg, item_ids, chunk_size=200):
    items_dict = {}
    unique_ids = list({int(i) for i in item_ids})
    for i in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[i:i + chunk_size]
        if not chunk:
            continue
        items = gg.items.get(ids=chunk)
        for item in items:
            items_dict[item['id']] = item
    return items_dict


def batch_get_prices(gg, item_ids, chunk_size=200):
    prices = {}
    unique_ids = list({int(i) for i in item_ids})
    for i in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[i:i + chunk_size]
        if not chunk:
            continue
        try:
            for entry in gg.commerceprices.get(ids=chunk):
                prices[entry['id']] = entry
        except HTTPError as e:
            # Untradable ids are left out of the reply. A chunk where nothing at all is
            # tradable 404s instead, which is not a failure - those items just have no price.
            if e.response is not None and e.response.status_code == 404:
                continue
            print(f"WARNING: price lookup failed for {len(chunk)} items, leaving them unpriced: {e}")
    return prices


def format_coin(copper):
    # 1 gold is exactly 10000 copper, so gold as a 4-decimal number reads off as gold.silver+copper
    return f"{copper / 10000:.4f}"


def item_value(oo, bound, items_dict, prices):
    """First rung that applies wins. A bound copy cannot be listed on the trading post,
    but a merchant will still buy it, so binding demotes a row rather than emptying it."""
    ii = items_dict.get(oo, {})
    pp = prices.get(oo)
    if not bound and pp and pp['sells']['unit_price'] > 0:
        return format_coin(pp['sells']['unit_price'] * TP_FEE_MULTIPLIER), 'TP'
    vendor_value = ii.get('vendor_value', 0)
    if vendor_value > 0 and 'NoSell' not in ii.get('flags', []):
        return format_coin(vendor_value), 'Vendor'
    return '', NO_VALUE_SOURCE


def append_item(result, jj, vv, ww, oo, items_dict, prices, bound, verbosity):
    ii = items_dict.get(oo, {})
    nn = ii.get('name', '')
    dd = ii.get('description', '')
    xx, zz = item_value(oo, bound, items_dict, prices)
    if verbosity:
        print("Adding element:", [jj, vv, ww, oo, nn, xx, zz, dd])
    result.append([jj, vv, ww, oo, nn, xx, zz, dd])


# takes in a results list, account name, nominal character name, a list of inventory entries,
# and a pre-fetched items dict. returns the results list with the contained items added.
# id_filter, when given, limits the entries to those item ids.
def search_list(result, jj, vv, ll, items_dict, prices, verbosity, id_filter=None):
    for item in ll:
        if item:
            oo = item['id']
            if id_filter is not None and oo not in id_filter:
                continue
            ww = item['count']
            append_item(result, jj, vv, ww, oo, items_dict, prices, bool(item.get('binding')), verbosity)
    return result

def get_value(wallet, id):
    for item in wallet:
        if item['id'] == id:
            return item['value']
    return 0

def main():
    parser = argparse.ArgumentParser(description='GW2 Item Extractor - Workhorse script')
    parser.add_argument('--api-keys', nargs='+', default=['api_keys.txt'], help='API key(s) or path to API keys file')
    parser.add_argument('--output', type=str, default='GW2_data_output.csv', help='Output CSV filename')
    parser.add_argument('--item-ids', nargs='+', help='Item ID(s) or path to item IDs file')
    parser.add_argument('--get-shared', action='store_true', help='Get shared inventory')
    parser.add_argument('--get-materials', action='store_true', help='Get materials storage')
    parser.add_argument('--get-bank', action='store_true', help='Get bank storage')
    parser.add_argument('--get-wallet', action='store_true', help='Get wallet currencies')
    parser.add_argument('--get-unfiltered', action='store_true', help='Get ALL items, ignore item-ids filter')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    # If no arguments provided, display README
    if len(sys.argv) == 1:
        display_readme()
        sys.exit(0)

    args = parser.parse_args()

    # Set flags
    get_shared = args.get_shared
    get_materials = args.get_materials
    get_bank = args.get_bank
    get_wallet = args.get_wallet
    get_unfiltered = args.get_unfiltered
    verbosity = args.verbose

    # Load item IDs if provided
    item_ids = []
    if args.item_ids:
        # Check if it's a file path (single argument that exists as file)
        if len(args.item_ids) == 1 and os.path.isfile(args.item_ids[0]):
            with open(args.item_ids[0], 'r') as f:
                item_ids = [int(line.strip()) for line in f.readlines() if line.strip()]
        else:
            # Treat as direct item IDs
            item_ids = [int(id) for id in args.item_ids]

    # Load API keys - can be file path or direct keys
    if len(args.api_keys) == 1 and os.path.isfile(args.api_keys[0]):
        # It's a file path
        api_keys = read_api_keys(args.api_keys[0])
        if not api_keys:
            print(f"ERROR: no API keys found in {args.api_keys[0]}")
            sys.exit(1)
    else:
        # Treat as direct API key(s)
        api_keys = args.api_keys

    # When the caller asked for specific items, that applies everywhere - storage
    # included, not just characters. It does not depend on the account, so work it
    # out once.
    id_filter = set(item_ids) if (item_ids and not get_unfiltered) else None

    # Currencies are not items. A wallet row carries a *currency* id in the Item ID
    # column, and the two namespaces overlap - 4 is both Gem and Assassin Transform
    # Weapon - so there is no honest way to apply an item filter to the wallet. A
    # filtered report therefore leaves the wallet out rather than padding itself with
    # every currency in the game, which is what made a one-item report unreadable.
    if get_wallet and id_filter is not None:
        print("NOTE: --get-wallet ignored because --item-ids was given - currencies are "
              "not items. Run with --get-unfiltered for wallet totals.")
        get_wallet = False

    result = []
    prices = {}            # item id -> trading post price, shared across accounts
    priced_ids = set()     # ids already looked up, tradable or not
    for aaa in api_keys:
        gg = GuildWars2Client(api_key=aaa)
        jj = gg.account.get()['name']

        # Phase 1: fetch account-level inventories
        inv_groups = []
        if get_shared:
            inv_groups.append((jj + '.shared', gg.accountinventory.get()))
        if get_materials:
            inv_groups.append((jj + '.materials', gg.accountmaterials.get()))
        if get_bank:
            inv_groups.append((jj + '.bank', gg.accountbank.get()))

        # Phase 2: fetch character inventories with retry
        char_invs = []
        cc = gg.characters.get()
        for vv in cc:
            max_retries = 3
            retry_delay = 2  # seconds
            ss = None
            for attempt in range(max_retries):
                try:
                    ss = gg.charactersinventory.get(vv)
                    break
                except HTTPError as e:
                    if e.response.status_code == 500:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1)
                            print(f"500 error on '{vv}', waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                            time.sleep(wait_time)
                        else:
                            print(f"ERROR: Failed to get '{vv}' after {max_retries} attempts, skipping.")
                    else:
                        print(f"ERROR: Non-500 error on '{vv}': {e}")
                        break
            char_invs.append((vv, ss))

        # Phase 3: collect every item id we'll need to render.
        all_ids = set()
        for _, inv in inv_groups:
            for item in inv:
                if item and (id_filter is None or item['id'] in id_filter):
                    all_ids.add(item['id'])
        for _, ss in char_invs:
            if ss is None:
                continue
            for bag in ss['bags']:
                if bag:
                    for item in bag.get('inventory', []):
                        if isinstance(item, dict) and item:
                            if id_filter is None or item['id'] in id_filter:
                                all_ids.add(item['id'])
        if not get_unfiltered:
            all_ids.update(item_ids)

        # Phase 4: one batched item lookup, then one batched price lookup
        items_dict = batch_get_items(gg, all_ids)
        unpriced = all_ids - priced_ids
        if unpriced:
            prices.update(batch_get_prices(gg, unpriced))
            priced_ids |= unpriced

        # Phase 5: emit rows in original order — account inventories, wallet, characters
        for vv, inv in inv_groups:
            result = search_list(result, jj, vv, inv, items_dict, prices, verbosity, id_filter)

        if get_wallet:
            vv = jj + '.wallet'
            wallet = gg.accountwallet.get()
            currency_ids = gg.currencies.get()
            all_currencies = gg.currencies.get(ids=currency_ids)
            for ccc in all_currencies:
                oo = ccc['id']
                ww = get_value(wallet, oo)
                nn = ccc['name']
                dd = ccc.get('description', '')
                if nn:
                    # Currencies have no trading post or vendor price
                    if verbosity:
                        print("Adding element:", [jj, vv, ww, oo, nn, '', NO_VALUE_SOURCE, dd])
                    result.append([jj, vv, ww, oo, nn, '', NO_VALUE_SOURCE, dd])

        for vv, ss in char_invs:
            if ss is None:
                continue
            if get_unfiltered:
                for bag in ss['bags']:
                    if bag:
                        for item in bag.get('inventory', []):
                            if isinstance(item, dict) and item:
                                ooo = item['id']
                                ww = item['count']
                                append_item(result, jj, vv, ww, ooo, items_dict, prices,
                                            bool(item.get('binding')), verbosity)
            else:
                for ooo in item_ids:
                    qq = [d for bag in ss['bags'] if bag for d in bag.get('inventory', []) if isinstance(d, dict) and d['id'] == ooo]
                    ww = sum(d['count'] for d in qq)
                    # One unbound copy means the trading post price is reachable for this row
                    bound = bool(qq) and all(d.get('binding') for d in qq)
                    append_item(result, jj, vv, ww, ooo, items_dict, prices, bound, verbosity)

    # Wallet currencies first - they are the account-wide totals, read at a glance,
    # and they do not belong buried between storage and character rows.
    wallet_rows = [row for row in result if str(row[1]).endswith('.wallet')]
    other_rows = [row for row in result if not str(row[1]).endswith('.wallet')]
    result = wallet_rows + other_rows

    df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item ID',
                                       'Item Name', 'Value', 'Source', 'Description'])

    # Create output directory if it doesn't exist (cross-platform)
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    df.to_csv(args.output, index=False)
    print("Saved to:", args.output)

if __name__ == '__main__':
    main()
