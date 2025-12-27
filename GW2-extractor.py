import pandas as pd
from gw2api import GuildWars2Client
from requests.exceptions import HTTPError
import time

verbosity = True  # Set to False if you don't want the "Adding element" lines to print
get_shared = False
get_materials = False
get_bank = False
get_wallet = False
item_ids = [70093]


# takes in a results list, account name, nominal character name and a list
# returns the results list with the contained items added
def search_list(result, jj, vv, ll):
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

with open('api_keys.txt', 'r') as opened_api_file:
    api_keys = [line.strip() for line in opened_api_file.readlines()]

result = []
for aaa in api_keys:
	gg = GuildWars2Client(api_key=aaa)
	jj = gg.account.get()['name']
	
	if get_shared:
		vv = jj + '.shared'
		inv = gg.accountinventory.get()
		result = search_list(result, jj, vv, inv)
	
	if get_materials:
		vv = jj + '.materials'
		inv = gg.accountmaterials.get()
		result = search_list(result, jj, vv, inv)
	
	if get_bank:
		vv = jj + '.bank'
		inv = gg.accountbank.get()
		result = search_list(result, jj, vv, inv)
	
	if get_wallet:
		vv = jj + '.wallet'
		wallet = gg.accountwallet.get()
		for currency in gg.currencies.get():
			ccc = gg.currencies.get(id=currency)
			ww = get_value(wallet,currency)
			nn = ccc['name']
			dd = ccc.get('description', '')
			oo = currency
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
filename = 'GW2_data_output.csv' 
df.to_csv(filename, index=False)
print("Saved to:", filename)
