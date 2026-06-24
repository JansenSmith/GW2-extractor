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

# takes in a results list, account name, nominal character name and a list
# returns the results list with the contained items added
def search_list(result, jj, vv, ll, gg, verbosity):
	for item in ll:
		if item:
			oo = item['id']
			ww = item['count']
			ii = gg.items.get(id=oo)
			nn = ii['name']
			dd = ii.get('description', '')
			if verbosity:
			    print("Adding element:", [jj, vv, ww, nn, oo, dd])
			result.append([jj, vv, ww, nn, oo, dd])
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
        with open(args.api_keys[0], 'r') as opened_api_file:
            api_keys = [line.strip() for line in opened_api_file.readlines()]
    else:
        # Treat as direct API key(s)
        api_keys = args.api_keys

    result = []
    for aaa in api_keys:
        gg = GuildWars2Client(api_key=aaa)
        jj = gg.account.get()['name']
        
        if get_shared:
            vv = jj + '.shared'
            inv = gg.accountinventory.get()
            result = search_list(result, jj, vv, inv, gg, verbosity)
        
        if get_materials:
            vv = jj + '.materials'
            inv = gg.accountmaterials.get()
            result = search_list(result, jj, vv, inv, gg, verbosity)
        
        if get_bank:
            vv = jj + '.bank'
            inv = gg.accountbank.get()
            result = search_list(result, jj, vv, inv, gg, verbosity)
        
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
                    if verbosity:
                        print("Adding element:", [jj, vv, ww, nn, oo, dd])
                    result.append([jj, vv, ww, nn, oo, dd])
                
        cc = gg.characters.get()
        for vv in cc:
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    ss = gg.charactersinventory.get(vv)
                    
                    if get_unfiltered:
                        # Get ALL items in character inventory
                        for bag in ss['bags']:
                            if bag:
                                for item in bag.get('inventory', []):
                                    if isinstance(item, dict) and item:
                                        ooo = item['id']
                                        ww = item['count']
                                        ii = gg.items.get(id=ooo)
                                        nn = ii['name']
                                        dd = ii.get('description', '')
                                        if verbosity:
                                            print("Adding element:", [jj, vv, ww, nn, ooo, dd])
                                        result.append([jj, vv, ww, nn, ooo, dd])
                    else:
                        # Filter by item_ids (original behavior)
                        for ooo in item_ids:
                            qq = [d['count'] for bag in ss['bags'] if bag for d in bag.get('inventory',[]) if isinstance(d, dict) and d['id'] == ooo]
                            ww = sum(qq)
                            ii = gg.items.get(id=ooo)
                            nn = ii['name']
                            dd = ii.get('description', '')
                            if verbosity:
                                print("Adding element:", [jj, vv, ww, nn, ooo, dd])
                            result.append([jj, vv, ww, nn, ooo, dd])
                    
                    break  # Success, exit retry loop
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

    df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item Name', 'Item ID', 'Description'])
    
    # Create output directory if it doesn't exist (cross-platform)
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    df.to_csv(args.output, index=False)
    print("Saved to:", args.output)

if __name__ == '__main__':
    main()
