import pandas as pd
from gw2api import GuildWars2Client
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

verbosity = True  # Set to False if you don't want the "Adding element"
get_shared = False
get_materials = False
get_bank = False 
get_wallet = False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
def make_request(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

item_ids = [70093]
#item_ids = [70093, 24517]

# local cacheing of item ids, names, and descriptions
class LocalCache:
    def __init__(self):
        self.cache = []

    def add_item(self, item_id, name, description):
        self.cache.append({'id': item_id, 'name': name, 'description': description})

    def check_cache(self, item_id):
        for item in self.cache:
            if item['id'] == item_id:
                return (item['name'], item.get('description', ''))
        # If the item is not found in the cache, call add_item and then check again
        item = gg.items.get(id=item_id)
        self.add_item(item_id, item['name'], item.get('description', ''))
        return self.check_cache(item_id)

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
itemCache = LocalCache()

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
		print("Working on:",vv)
		ss = gg.charactersinventory.get(vv)
		
		# make sure the API hasn't changed
		if len(list(ss.keys())) != 1 or list(ss.keys())[0] != 'bags':
			raise Exception("GW2 API has changed; contact Jansen.")
		
		# concatenate all the items in all the character's bags together, ignoring empty bags
		items = []
		for ooo in ss:
			items.extend([item for bag in ss['bags'] if bag and bag['inventory'] is not None for item in bag['inventory']])
			
		# get rid of empty item slots
		items = [item for item in items if item is not None and item != {}]
		
		# total all the stacks
		item_counts = [{'id': k, 'total': sum(i['count'] for i in [x for x in items if isinstance(x, dict) and x['id'] == k])} for k in set([x['id'] for x in items if isinstance(x, dict)])]
		
		# for each item, make an entry in the resultant spreadsheet
		for item in item_counts:
			item_id = item['id']
			amt = item['total']
			name, description = itemCache.check_cache(item_id)
			if verbosity:
				print("Adding element:", [jj, vv, amt, name, item_id, description])
			result.append([jj, vv, amt, name, item_id, description])

df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item Name', 'Item ID', 'Description'])

filename = 'GW2_data_output.csv' 
df.to_csv(filename, index=False)
print("Saved to:", filename)
