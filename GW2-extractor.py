import pandas as pd
from gw2api import GuildWars2Client

# takes in a results list, account name, nominal character name and a list
# returns the results list with the contained items added
def search_list(result, jj, vv, ll):
	for item in ll:
		if item:
			oo = item['id']
			ww = item['count']
			ii = gg.items.get(id=oo)
			nn = ii['name']
			##dd = ii['description']
			if verbosity:
			    print("Adding element:", [jj, vv, ww, nn, oo])
			result.append([jj, vv, ww, nn, oo])
	return result

def get_value(wallet, id):
    for item in wallet:
        if item['id'] == id:
            return item['value']
    return 0

with open('api_keys.txt', 'r') as opened_api_file:
    api_keys = [line.strip() for line in opened_api_file.readlines()]

item_ids = [70093, 24517]

result = []
verbosity = True  # Set to False if you don't want the "Adding element"

for aaa in api_keys:
	gg = GuildWars2Client(api_key=aaa)

	jj = gg.account.get()['name']
	
	vv = jj + '.shared'
	inv = gg.accountinventory.get()
	result = search_list(result, jj, vv, inv)
	
	vv = jj + '.materials'
	inv = gg.accountmaterials.get()
	result = search_list(result, jj, vv, inv)
	
	vv = jj + '.bank'
	inv = gg.accountbank.get()
	result = search_list(result, jj, vv, inv)
	

df = pd.DataFrame(result, columns=['Account Name', 'Character Name', 'Amount', 'Item Name', "Item ID"])

filename = 'GW2_account_output.csv' 
df.to_csv(filename, index=False)
print("Saved to:", filename)
