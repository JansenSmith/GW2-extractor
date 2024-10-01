import pandas as pd
from gw2api import GuildWars2Client

verbosity = True  # Set to False if you don't want the "Adding element"
get_materials = False

item_ids = 70093
#item_ids = [70093, 24517]

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
	
	vv = jj + '.shared'
	inv = gg.accountinventory.get()
	result = search_list(result, jj, vv, inv)
	
	if get_materials:
		vv = jj + '.materials'
		inv = gg.accountmaterials.get()
		result = search_list(result, jj, vv, inv)
	
	vv = jj + '.bank'
	inv = gg.accountbank.get()
	result = search_list(result, jj, vv, inv)
	
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

df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item Name', 'Item ID', 'Description'])

filename = 'GW2_data_output.csv' 
df.to_csv(filename, index=False)
print("Saved to:", filename)
